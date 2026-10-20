"""REAL UI preparation and controlled paid-transport simulation; zero remote calls."""
import json
import sqlite3
from pathlib import Path
from urllib.error import URLError
import pytest
from fastapi import HTTPException
from backend import main,database,luna_real_ui as ui,luna_sync_runtime as sync
from backend.luna_application import request_key

@pytest.fixture
def service(tmp_path,monkeypatch):
    source=ui.ROOT/'docs/step4_final_20261016/verified/application.db'
    path=tmp_path/'application.db'
    c=sqlite3.connect('file:'+source.resolve().as_posix()+'?mode=ro',uri=True);d=sqlite3.connect(path);c.backup(d);c.close()
    ids=[r[0] for r in d.execute('SELECT id FROM evaluations WHERE response_id=155')]
    for eid in ids:
        for table in ('evaluation_criteria','evaluation_indicators','evaluation_strengths','evaluation_improvements','evaluation_alerts'):d.execute(f'DELETE FROM {table} WHERE evaluation_id=?',(eid,))
        d.execute('DELETE FROM evaluations WHERE id=?',(eid,))
    d.commit();d.close()
    def connect():
        con=sqlite3.connect(path);con.row_factory=sqlite3.Row;return con
    monkeypatch.setattr(main,'get_connection',connect);monkeypatch.setattr(database,'DB_PATH',path)
    monkeypatch.setenv('OPENAI_API_KEY','controlled-test-placeholder-never-transmitted')
    monkeypatch.setattr(ui.luna_credentials,'load',lambda:True)
    return ui.RealService(main,tmp_path/'jobs',archive={})

class Response:
    status=200
    headers={'x-request-id':'controlled-offline-fixture-not-real-HTTP'}
    def __init__(self,raw):self.raw=raw
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self):return json.dumps(self.raw).encode()

def test_prepare_collects_exact_requests_without_network_grant_or_key_disclosure(service,monkeypatch):
    monkeypatch.setattr(sync,'urlopen',lambda *a,**k:pytest.fail('Preparation must never call an API'))
    state=service.prepare([155]);folder=service.folder(state['id'])
    assert state['status']=='prepared' and state['total_requests']==22
    assert not (folder/'budget.json').exists() and not (folder/'authorization.json').exists()
    assert state['completed_requests']==0 and state['actual_cost_usd']=='0'
    assert 'controlled-test-placeholder' not in json.dumps(service.status())

def test_confirmation_and_budget_are_required_before_worker(service):
    state=service.prepare([155])
    with pytest.raises(HTTPException):service.confirm(state['id'],'NO',state['estimated_reserve_usd'],start=False)
    with pytest.raises(HTTPException):service.confirm(state['id'],'AUTORIZO','0',start=False)
    assert not (service.folder(state['id'])/'authorization.json').exists()

def test_full_actual_runner_from_ui_job_uses_22_controlled_receipts_and_persists_na(service,monkeypatch):
    lineage=ui.read(ui.ROOT/'docs/economic_readers_step3_2_20261016/adjudicated_final_20261016/followup_v17/ENTREGA_FINAL/LINaje_56_Cuerpos.json')
    known={r['key']:ui.read(r['raw_response']) for r in lineage}
    calls=[]
    def fake_open(request,**kwargs):
        body=json.loads(request.data);key=request_key(body,request.full_url.split('/v1/')[1])[0]
        assert key in known;calls.append(key);return Response(known[key])
    monkeypatch.setattr(sync,'urlopen',fake_open)
    state=service.prepare([155]);pid=state['id']
    service.confirm(pid,'AUTORIZO',state['estimated_reserve_usd'],start=False)
    service.work(pid)
    done=service.state(pid)
    assert done['status']=='complete' and len(set(calls))==len(calls)==22
    assert done['completed_requests']==22 and done['uncertain_requests']==0
    result=main._load_saved_evaluation(155)['result']
    bycode={r['code']:r for r in result['indicator_results']}
    assert len(bycode)==104
    assert bycode['CR-RE1']['status']==bycode['CR-AC6']['status']=='N/A'
    assert bycode['CR-RE1']['verified_decisions']['CR-RE1.gate']['value'] is None
    before=len(calls);service.confirm(pid,'AUTORIZO',state['estimated_reserve_usd'],start=False)
    assert len(calls)==before
    with pytest.raises(HTTPException):service.prepare([155])

def test_uncertain_transmission_preserves_reservation_and_cannot_duplicate_or_resume(service,monkeypatch):
    calls=[]
    def fail(*args,**kwargs):calls.append(1);raise URLError('controlled offline interruption')
    monkeypatch.setattr(sync,'urlopen',fail)
    state=service.prepare([155]);pid=state['id']
    service.confirm(pid,'AUTORIZO',state['estimated_reserve_usd'],start=False);service.work(pid)
    stopped=service.state(pid)
    assert len(calls)==1 and stopped['status']=='stopped_requires_review'
    assert stopped['uncertain_requests']==1 and not stopped['can_resume']
    assert float(stopped['reserved_usd'])>0
    with pytest.raises(HTTPException):service.start(pid)
    other=service.prepare([155])
    with pytest.raises(HTTPException):service.confirm(other['id'],'AUTORIZO',other['estimated_reserve_usd'],start=False)
    assert len(calls)==1

def test_connection_probe_is_two_blind_schema_checked_calls_only_after_consent(service,monkeypatch):
    calls=[]
    def fake_open(request,**kwargs):
        body=json.loads(request.data);calls.append(body)
        return Response(dict(model='gpt-6-luna',status='completed',id='synthetic-fixture',
            output=[dict(type='message',role='assistant',status='completed',phase='final_answer',id='synthetic-message',
                         content=[dict(type='output_text',text='{"ok":true}')])],usage=dict(input_tokens=100,output_tokens=8)))
    monkeypatch.setattr(sync,'urlopen',fake_open)
    state=service.prepare([],True);assert not calls
    service.confirm(state['id'],'AUTORIZO',state['estimated_reserve_usd'],start=False);service.work(state['id'])
    assert len(calls)==2 and calls[0]!=calls[1]
    assert all('ok' not in c['input'][0]['content'] for c in calls)
    assert service.state(state['id'])['status']=='complete'
    assert service.status()['connection']['status']=='verified_by_two_real_requests'

def test_selection_cannot_authorize_950_or_duplicate_ids(service):
    for ids in ([155,155],list(range(1,27)),[]):
        with pytest.raises(HTTPException):service.prepare(ids)

def test_original_receipts_are_reused_instead_of_duplicating_completed_api(service,monkeypatch,tmp_path):
    monkeypatch.setattr(sync,'urlopen',lambda *a,**k:pytest.fail('Historical receipts must never be retransmitted'))
    archived=ui.RealService(main,tmp_path/'archived_jobs')
    state=archived.prepare([155])
    assert state['status']=='complete' and state['total_requests']==0
    assert state['historical_reused_requests']==22 and state['actual_cost_usd']=='0'
    assert not (archived.folder(state['id'])/'authorization.json').exists()
    assert main._load_saved_evaluation(155)['result']['evaluation_state']=='complete'

def test_budget_reserved_durably_before_any_worker_or_transmission(service,monkeypatch):
    monkeypatch.setattr(sync,'urlopen',lambda *a,**k:pytest.fail('No worker was started'))
    state=service.prepare([],True)
    confirmed=service.confirm(state['id'],'AUTORIZO',state['estimated_reserve_usd'],start=False)
    assert confirmed['confirmed'] and not confirmed['worker_running']
    assert confirmed['reserved_usd']==state['estimated_reserve_usd']
    assert confirmed['completed_requests']==0

def test_historical_uncertain_keys_never_become_payable_plans(service,monkeypatch):
    protected=next(iter(ui.FORBIDDEN_UNCERTAIN_REQUESTS))
    monkeypatch.setattr(ui,'request_key',lambda *args:(protected,b''))
    with pytest.raises(HTTPException) as error:service.prepare([155])
    assert error.value.status_code==409
    assert not list(service.root.glob('plans/*/authorization.json'))
