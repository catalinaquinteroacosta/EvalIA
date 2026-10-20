import json
from hashlib import sha256
from pathlib import Path
import pytest
from backend import luna_reader
from backend.luna_budget import BudgetJournal,BudgetBlocked
from backend.luna_sync_runtime import SealedSyncTransport


def prepare(tmp_path,n=1):
    body=dict(model='gpt-6-luna',max_output_tokens=100,input=[])
    rows=[dict(endpoint='responses',body=dict(body,seed=i)) for i in range(n)]
    from backend import luna_runner,luna_sync_runtime
    sources={name:sha256(Path(module.__file__).read_bytes()).hexdigest() for name,module in
        (('luna_reader',luna_reader),('luna_runner',luna_runner),('luna_sync_runtime',luna_sync_runtime))}
    manifest=dict(reader_sha256=sources['luna_reader'],runtime_sources=sources,allowed_experiment_ids=[999],requests=rows)
    path=tmp_path/'manifest.json';path.write_text(json.dumps(manifest))
    j=BudgetJournal(tmp_path/'budget.json');j.initialize(prior_evidence='offline test only')
    auth=dict(mode='sync',model='gpt-6-luna',explicit_user_approval=True,allowed_experiment_ids=[999],
        manifest_path=str(path),sealed_manifest_sha256=sha256(path.read_bytes()).hexdigest(),
        private_directory=str(tmp_path/'private'),budget_journal=str(j.path),run_id='test',scope='offline only',
        max_usd='1',max_requests=n,allow_definitive_950=False)
    ap=tmp_path/'authorization.json';ap.write_text(json.dumps(auth))
    return SealedSyncTransport(ap),rows,j


class Response:
    status=200
    headers={'x-request-id':'controlled-offline-request-id'}
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self):return json.dumps(dict(id='synthetic-offline',model='gpt-6-luna',usage=dict(input_tokens=10,output_tokens=5,input_tokens_details={}))).encode()


def test_network_failure_records_reason_and_still_forbids_retry(tmp_path,monkeypatch):
    from urllib.error import URLError
    t,rows,j=prepare(tmp_path)
    monkeypatch.setenv('OPENAI_API_KEY','offline-placeholder')
    calls=[]
    def network(*args,**kwargs):
        calls.append(1)
        raise URLError(OSError(10013,'controlled offline network denial'))
    monkeypatch.setattr('backend.luna_sync_runtime.urlopen',network)
    with pytest.raises(RuntimeError,match='sync_request_failed_reserved_no_retry'):
        t(rows[0]['body'],rows[0]['endpoint'])
    proof=json.loads(next(t.root.glob('*.failure.json')).read_text())
    assert proof['network_errno']==10013
    assert 'controlled offline network denial' in proof['network_reason']
    assert proof['transmission_status']=='uncertain_no_retry'
    with pytest.raises(BudgetBlocked,match='uncertain_sync_request_no_retry_or_continuation'):
        t(rows[0]['body'],rows[0]['endpoint'])
    assert len(calls)==1 and j.snapshot()['reserved_usd']=='1'


def test_success_reserved_before_network_and_replay_never_resends(tmp_path,monkeypatch):
    t,rows,j=prepare(tmp_path); calls=[]
    monkeypatch.setenv('OPENAI_API_KEY','offline-placeholder')
    def network(*a,**k):
        assert j.snapshot()['reserved_usd']=='1'
        assert list(t.root.glob('*.intent.json'))
        calls.append(1);return Response()
    monkeypatch.setattr('backend.luna_sync_runtime.urlopen',network)
    first=t(rows[0]['body'],'responses');assert t(rows[0]['body'],'/v1/responses')==first
    assert len(calls)==1 and j.snapshot()['reserved_usd']=='0'
    receipt=json.loads(next(t.root.glob('*.receipt.json')).read_text())
    assert receipt['http_status']==200
    assert receipt['remote_request_id']=='controlled-offline-request-id'
    assert receipt['model']=='gpt-6-luna' and receipt['endpoint']=='responses'


def test_failure_preserves_reserve_and_blocks_remaining_and_restart(tmp_path,monkeypatch):
    t,rows,j=prepare(tmp_path,2);monkeypatch.setenv('OPENAI_API_KEY','offline-placeholder')
    calls=[]
    def fail(*a,**k):calls.append(1);raise TimeoutError()
    monkeypatch.setattr('backend.luna_sync_runtime.urlopen',fail)
    with pytest.raises(RuntimeError):t(rows[0]['body'],'responses')
    with pytest.raises(BudgetBlocked):t(rows[0]['body'],'responses')
    with pytest.raises(BudgetBlocked):t(rows[1]['body'],'responses')
    assert len(calls)==1 and j.snapshot()['reserved_usd']=='1'


def test_unsealed_request_rejected_before_network(tmp_path,monkeypatch):
    t,rows,j=prepare(tmp_path)
    monkeypatch.setattr('backend.luna_sync_runtime.urlopen',lambda *a,**k:pytest.fail('network forbidden'))
    with pytest.raises(BudgetBlocked):t(dict(rows[0]['body'],max_output_tokens=101),'responses')
    assert not list(t.root.glob('*.intent.json'))


def test_global_budget_block_rejected_before_network(tmp_path,monkeypatch):
    t,rows,j=prepare(tmp_path)
    with j.lock:
        state=j._load();state['blocked_reasons'].append('offline adversarial block');j._write(state)
    monkeypatch.setattr('backend.luna_sync_runtime.urlopen',lambda *a,**k:pytest.fail('network forbidden'))
    with pytest.raises(BudgetBlocked):t(rows[0]['body'],'responses')
    assert not list(t.root.glob('*.intent.json'))


def test_explicit_mount_uses_luna_runner_without_network_or_qualification_bypass(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from backend.luna_sync_runtime import configure
    t,rows,j=prepare(tmp_path)
    monkeypatch.setattr('backend.luna_sync_runtime.urlopen',lambda *a,**k:pytest.fail('network forbidden'))
    app=SimpleNamespace(state=SimpleNamespace())
    configured=configure(app,tmp_path/'authorization.json')
    deps=app.state.evaluation_dependencies
    assert deps['paid_mode']=='sync' and deps['allowed_experiment_ids']==frozenset([999])
    assert deps['runner_factory'].__module__=='backend.luna_runner'
    assert deps['crisis_provider'].qualified('CR-RI2') is False
    assert deps['crisis_provider'].qualified('CR-CE10') is False
    assert not list(configured.root.glob('*.intent.json'))


def test_http_rejection_preserves_original_bytes_and_request_id(tmp_path,monkeypatch):
    from urllib.error import HTTPError
    from io import BytesIO
    t,rows,j=prepare(tmp_path);monkeypatch.setenv('OPENAI_API_KEY','offline-placeholder')
    def fail(*args,**kwargs):
        raise HTTPError('https://api.openai.com/v1/responses',403,'Forbidden',{'x-request-id':'synthetic-offline-rejection'},BytesIO(b'{"error":"offline fixture"}'))
    monkeypatch.setattr('backend.luna_sync_runtime.urlopen',fail)
    with pytest.raises(RuntimeError):t(rows[0]['body'],'responses')
    assert next(t.root.glob('*.http_error.bin')).read_bytes()==b'{"error":"offline fixture"}'
    failure=json.loads(next(t.root.glob('*.failure.json')).read_text())
    assert failure['http_status']==403 and failure['remote_request_id']=='synthetic-offline-rejection'
    assert j.snapshot()['reserved_usd']=='1'
