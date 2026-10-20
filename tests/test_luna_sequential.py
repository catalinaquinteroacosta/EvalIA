import json
from pathlib import Path
from hashlib import sha256
from decimal import Decimal
import pytest
from urllib.error import URLError
from backend import luna_reader as r,luna_runner,luna_sync_runtime as sync
from backend.luna_sequential import SequentialTransport
from backend.luna_budget import BudgetBlocked

class Reply:
 status=200;headers={}
 def __enter__(self):return self
 def __exit__(self,*a):pass
 def read(self):return json.dumps({'model':r.MODEL,'usage':{'prompt_tokens':1000,'completion_tokens':1000},'choices':[]}).encode()

def prepare(tmp_path,monkeypatch,cap='3',rows=None):
 source=Path('.evalia-private/luna_ui/plans/f2ca66042f384c6289cb485168c284cd/manifest.json')
 manifest=json.loads(source.read_text(encoding='utf8'))
 if rows is not None:manifest['requests']=rows
 manifest['runtime_sources']={n:sha256(Path(mod.__file__).read_bytes()).hexdigest() for n,mod in [('luna_reader',r),('luna_runner',luna_runner),('luna_sync_runtime',sync)]}
 p=tmp_path/'manifest.json';p.write_text(json.dumps(manifest),encoding='utf8')
 c=dict(mode='sync',execution_policy='sequential_per_request',model=r.MODEL,explicit_user_approval=True,allowed_experiment_ids=[108],manifest_path=str(p),sealed_manifest_sha256=sha256(p.read_bytes()).hexdigest(),private_directory=str(tmp_path/'receipts'),budget_journal=str(tmp_path/'budget.json'),run_id='test108',scope='controlled test',max_requests=len(manifest['requests']),max_usd=cap,allow_definitive_950=False)
 auth=tmp_path/'auth.json';auth.write_text(json.dumps(c),encoding='utf8');monkeypatch.setenv('OPENAI_API_KEY','fake-never-remote');return auth,manifest['requests']

def test_all_850_original_bodies_replay_restart_and_settle(tmp_path,monkeypatch):
 auth,rows=prepare(tmp_path,monkeypatch);calls=[]
 monkeypatch.setattr(sync,'urlopen',lambda *a,**k:(calls.append(1) or Reply()))
 t=SequentialTransport(auth)
 assert len(t.requests)==850
 for row in rows:t(row['body'],row['endpoint'])
 assert len(calls)==850
 snapshot=t.journal.snapshot();assert Decimal(snapshot['spent_usd'])==Decimal('.51') and snapshot['reserved_usd']=='0'
 t=SequentialTransport(auth)
 for row in rows:t(row['body'],row['endpoint'])
 assert len(calls)==850 and t.journal.snapshot()==snapshot

def test_budget_stops_before_send_and_reservation_is_durable(tmp_path,monkeypatch):
 source=json.loads(Path('.evalia-private/luna_ui/plans/f2ca66042f384c6289cb485168c284cd/manifest.json').read_text(encoding='utf8'))['requests']
 rows=sorted(source,key=lambda row:Decimal(r.estimate_reserve(row['body'],'sync')['reserved_usd']),reverse=True)[:2]
 cap=str(max(Decimal(r.estimate_reserve(x['body'],'sync')['reserved_usd']) for x in rows)+Decimal('.0001'))
 auth,rows=prepare(tmp_path,monkeypatch,cap,rows);t=SequentialTransport(auth);calls=[]
 def send(*a,**k):
  assert Decimal(t.journal.snapshot()['reserved_usd'])>0
  calls.append(1);return Reply()
 monkeypatch.setattr(sync,'urlopen',send)
 t(rows[0]['body'],rows[0]['endpoint'])
 with pytest.raises(BudgetBlocked):t(rows[1]['body'],rows[1]['endpoint'])
 assert len(calls)==1
 assert Decimal(t.journal.snapshot()['spent_usd'])==Decimal('.0006')
 assert t.journal.snapshot()['reserved_usd']=='0'

def test_uncertain_holds_and_never_retries_after_restart(tmp_path,monkeypatch):
 auth,rows=prepare(tmp_path,monkeypatch);calls=[]
 def fail(*a,**k):calls.append(1);raise URLError('controlled timeout')
 monkeypatch.setattr(sync,'urlopen',fail);t=SequentialTransport(auth)
 with pytest.raises(RuntimeError):t(rows[0]['body'],rows[0]['endpoint'])
 assert Decimal(t.journal.snapshot()['reserved_usd'])>0
 t=SequentialTransport(auth)
 for row in rows[:2]:
  with pytest.raises(BudgetBlocked):t(row['body'],row['endpoint'])
 assert len(calls)==1

def test_changed_body_and_cap_rejected(tmp_path,monkeypatch):
 auth,rows=prepare(tmp_path,monkeypatch);t=SequentialTransport(auth);body={**rows[0]['body'],'store':True}
 with pytest.raises(BudgetBlocked):t(body,rows[0]['endpoint'])
 c=json.loads(auth.read_text());c['max_usd']='3.01';auth.write_text(json.dumps(c))
 with pytest.raises(BudgetBlocked):SequentialTransport(auth)

def test_108_confirmation_is_sequential_and_does_not_transmit(tmp_path,monkeypatch):
    import shutil
    from backend import main,database,luna_real_ui
    from fastapi import HTTPException
    db=tmp_path/'db.sqlite';shutil.copyfile('.evalia-private/luna_ui/application.db',db)
    monkeypatch.setattr(database,'DB_PATH',db)
    monkeypatch.setattr(luna_real_ui.luna_credentials,'available',lambda:True)
    service=luna_real_ui.RealService(main,tmp_path/'service',archive={})
    pid='a'*32;folder=service.root/'plans'/pid;folder.mkdir(parents=True)
    original=json.loads(Path('.evalia-private/luna_ui/plans/f2ca66042f384c6289cb485168c284cd/manifest.json').read_text(encoding='utf8'))
    (folder/'manifest.json').write_text(json.dumps(original),encoding='utf8')
    state=dict(id=pid,status='prepared',confirmed=False,experiment_ids=[108],connection_test=False,database_sha_scope=str(db.resolve()),estimated_reserve_usd='42.21702150',total_requests=850,response_ids=[999],actual_cost_usd='0',results=[])
    (folder/'state.json').write_text(json.dumps(state),encoding='utf8')
    monkeypatch.setattr(sync,'urlopen',lambda *a,**k:pytest.fail('No API allowed'))
    with pytest.raises(HTTPException):service.confirm(pid,'AUTORIZO','3.01',start=False)
    result=service.confirm(pid,'AUTORIZO','3.00',start=False)
    auth=json.loads((folder/'authorization.json').read_text())
    assert auth['execution_policy']=='sequential_per_request' and auth['max_usd']=='3.00'
    assert result['reserved_usd']=='0' and result['completed_requests']==0 and result['budget_remaining_usd']=='3.00'
    transport=SequentialTransport(folder/'authorization.json')
    assert transport.journal.snapshot()['cap_usd']=='3.00'

def test_receipt_survives_crash_before_settlement(tmp_path,monkeypatch):
    auth,rows=prepare(tmp_path,monkeypatch)
    monkeypatch.setattr(sync,'urlopen',lambda *a,**k:Reply())
    t=SequentialTransport(auth);t(rows[0]['body'],rows[0]['endpoint'])
    path=tmp_path/'budget.json';state=json.loads(path.read_text())
    entry=next(iter(state['entries'].values()));entry['status']='reserved'
    for key in ('actual_usd','actual_requests','usage_evidence'):entry.pop(key,None)
    path.write_text(json.dumps(state))
    monkeypatch.setattr(sync,'urlopen',lambda *a,**k:pytest.fail('Must recover receipt without sending'))
    recovered=SequentialTransport(auth)
    assert recovered.journal.snapshot()['reserved_usd']=='0'
    recovered(rows[0]['body'],rows[0]['endpoint'])
    assert Decimal(recovered.journal.snapshot()['spent_usd'])==Decimal('.0006')
