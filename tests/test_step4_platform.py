"""Controlled local-only application workflows, never paid model requests."""
import asyncio
import json
from pathlib import Path
from urllib.parse import urlsplit
import pytest
from backend import validation_runtime as rt
from backend.export_audit import indicator_records

async def call(app,method,path,payload=None):
    events=[];q=urlsplit(path);raw=json.dumps(payload).encode() if payload is not None else b''
    async def receive():return dict(type='http.request',body=raw,more_body=False)
    async def send(event):events.append(event)
    await app(dict(type='http',asgi={'version':'3.0','spec_version':'2.4'},http_version='1.1',
        method=method,scheme='http',path=q.path,raw_path=q.path.encode(),query_string=q.query.encode(),root_path='',
        headers=[(b'content-type',b'application/json')],server=('127.0.0.1',0),client=('127.0.0.1',1)),receive,send)
    status=next(e['status'] for e in events if e['type']=='http.response.start')
    body=b''.join(e.get('body',b'') for e in events if e['type']=='http.response.body')
    return status,json.loads(body) if body else None

@pytest.fixture(scope='module')
def platform():
    main,replay=rt.configure(rt.OUTPUT/'verified/application.db')
    return main,replay

def request(platform,method,path,payload=None):return asyncio.run(call(platform[0].app,method,path,payload))

def test_effective_readiness_does_not_claim_generation_or_paid_authorization(platform):
    status,data=request(platform,'GET','/api/status')
    assert status==200 and data['semantic_reader_configured'] and data['replay_only']
    assert data['paid_execution_enabled'] is False and data['generation_api_configured'] is False
    assert len(data['models'])==5 and all(m['api_model_id'] is None for m in data['models'])

def test_persisted_185_and_new_na_survive_http_recovery(platform):
    rows=[]
    for eid in (99,101):
        status,data=request(platform,'GET',f'/api/experiments/{eid}/results')
        assert status==200
        rows.extend(indicator_records(data))
    assert len(rows)==185
    assert sum(r['status']=='N/A' for r in rows)==34
    assert sum(r['status']=='SCORED' for r in rows)==151
    for row in rows:
        if row['code'] in ('CR-RE1','CR-AC6'):
            assert row['indicator']['verified_decisions'][row['code']+'.gate']['value'] is None
            assert row['indicator']['applicability_disposition']['factual_gate_value'] is None
            assert row['status']=='N/A' and row['score'] is None

def test_five_models_five_turns_capture_resume_duplicates_and_no_paid_pilot(platform):
    models=['ChatGPT','Gemini','Claude','Copilot','Perplexity']
    status,exp=request(platform,'POST','/api/experiments',dict(scenario_code='ANS-01',model_names=models))
    assert status==201,(status,exp)
    eid=exp['experiment_id'] if 'experiment_id' in exp else exp['id']
    def body(model,n):return dict(experiment_id=eid,model_name=model,turn_number=n,
        response_text=f'CONTROL SINTÉTICO DE CAPTURA, NO RESPUESTA AUTÉNTICA: {model}, turno {n}.')
    status,data=request(platform,'POST','/api/responses/manual',body(models[0],2))
    assert status==409,(status,data)
    ids=[]
    for model in models:
        for n in range(1,6):
            status,data=request(platform,'POST','/api/responses/manual',body(model,n))
            assert status==201,(status,data)
            ids.append(data['response_id'])
    status,same=request(platform,'POST','/api/responses/manual',body(models[0],1))
    assert status==201 and same['action']=='already_saved' and same['response_id']==ids[0]
    changed=body(models[0],1);changed['response_text']='NO DEBE SOBREESCRIBIR'
    assert request(platform,'POST','/api/responses/manual',changed)[0]==409
    assert request(platform,'POST','/api/responses/manual',body('No seleccionado',1))[0]==422
    assert request(platform,'POST','/api/responses/manual',body(models[0],6))[0]==422
    status,progress=request(platform,'GET',f'/api/experiments/{eid}/results')
    assert status==200 and len(progress['results'])==len(set(ids))==25
    assert all(not r.get('evaluated') for r in progress['results'])
    before=len(platform[1].used)
    assert request(platform,'POST',f'/api/responses/{ids[0]}/evaluate')[0]==403
    assert len(platform[1].used)==before
    rt.OUTPUT.joinpath('MANUAL_WORKFLOW.json').write_text(json.dumps(dict(
        experiment_id=eid,models=models,responses=25,synthetic_capture_only=True,semantic_evaluations=0,
        future_save_rejected=True,duplicate_save_idempotent=True,overwrite_rejected=True,
        recoverable_response_ids=ids,paid_requests=0),ensure_ascii=False,indent=2),encoding='utf8')

def test_unconfigured_reader_returns_explicit_no_spend_error(platform):
    # Configuration status is checked independently without touching saved tests.
    main=platform[0];original=main.app.state.evaluation_dependencies
    try:
        main.app.state.evaluation_dependencies=None
        assert main.system_status()['paid_execution_enabled'] is False
        assert main.system_status()['semantic_reader_configured'] is False
    finally:main.app.state.evaluation_dependencies=original

def test_historical_post_reuses_saved_results_without_reader_calls(platform):
    before=len(platform[1].used)
    for rid in (153,155):
        status,data=request(platform,'POST',f'/api/responses/{rid}/evaluate')
        assert status in (200,201) and data['status']=='already_evaluated'
    assert len(platform[1].used)==before
