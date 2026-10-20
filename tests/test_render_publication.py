from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile
import pytest
from backend.published_results import PublishedResults,FORMAT,clean_presentation

def make_archive(tmp_path,extra=None):
    from backend.global_results import aggregate
    global_data=dict(aggregate([],[]),version='test',bank='test',experiments=[],excluded=[],method=[],generated_at='test',dataset_id='test')
    record=dict(id=108,code='ANS-01',title='Caso simulado',category='Ansiedad',url='/resultados?experiment_id=108',rubric_type='trastorno',status='evaluated')
    global_data['experiments']=[record]
    members={'global.json':global_data,'experiments/108.json':dict(details=dict(id=108,historical_read_only=True),
        results=dict(experiment=dict(id=108),results=[dict(response_id=194,response_text='Respuesta simulada')]))}
    encoded={k:json.dumps(v).encode() for k,v in members.items()}
    manifest=dict(format=FORMAT,experiments=[record],response_ids=[194],bank='test',members={k:sha256(v).hexdigest() for k,v in encoded.items()})
    path=tmp_path/'results.zip'
    with ZipFile(path,'w') as z:
        for name,value in encoded.items():z.writestr(name,value)
        z.writestr('manifest.json',json.dumps(manifest))
        if extra:z.writestr(*extra)
    return path,sha256(path.read_bytes()).hexdigest()

def test_published_results_verified_and_no_private_entries(tmp_path):
    path,digest=make_archive(tmp_path)
    archive=PublishedResults(path,digest)
    assert archive.experiment(108)['details']['historical_read_only']
    with pytest.raises(KeyError):archive.experiment(109)
    with pytest.raises(ValueError,match='SHA-256'):PublishedResults(path,'0'*64)
    archive.archive.close()
    path,digest=make_archive(tmp_path,('../private.db','secret'))
    with pytest.raises(ValueError,match='no autorizados'):PublishedResults(path,digest)

def test_public_fields_keep_scores_and_rationale_without_internal_artifacts():
    source=dict(score=0,justification='Falta la conducta',status='SCORED',manual_evaluator='identity',
        validated_audit=dict(receipt_path='private'),nested=[dict(score=None,status='N/A',proposal='private')])
    assert clean_presentation(source)==dict(score=0,justification='Falta la conducta',status='SCORED',nested=[dict(score=None,status='N/A')])

def test_cloud_process_preserves_research_and_separates_new_experiments(tmp_path):
    path,digest=make_archive(tmp_path)
    root=Path(__file__).resolve().parents[1]
    env=dict(os.environ,EVALIA_RESULTS_FILE=str(path),EVALIA_RESULTS_SHA256=digest,EVALIA_WORK_DIR=str(tmp_path/'work'),
        EVALIA_PUBLIC_ORIGIN='https://example.onrender.com',PYTHONPATH=os.pathsep.join(sys.path))
    env.pop('OPENAI_API_KEY',None)
    code='''
from fastapi.testclient import TestClient
from backend.render_app import create_app
app=create_app()
with TestClient(app) as c:
    assert c.get('/healthz').json()['original_experiments']==1
    assert c.get('/api/experiments/108/results').json()['experiment']['id']==108
    assert c.get('/api/experiments').json()['total']==1
    assert c.get('/api/results/catalog').json()['experiments'][0]['id']==108
    assert c.post('/api/experiments/108/free-turns',json={'user_message':'change'}).status_code==403
    assert c.post('/api/responses/manual',json={'experiment_id':108}).status_code==403
    assert c.post('/api/real/prepare',json={'response_ids':[194]}).status_code==403
    result=c.post('/api/experiments',json={'scenario_code':'ANS-01','model_names':['ChatGPT']})
    assert result.status_code in (200,201),result.text
    experiment=result.json()
    assert experiment['experiment_id']>10000,experiment
    assert c.get('/api/experiments').json()['total']==2
    assert c.get('/api/real/status').json()['credential_present'] is False
    assert c.get('/api/deployment').json()['temporary_experiments']
    blocked=c.post('/api/real/not-a-plan/confirm',json={'confirmation':'AUTORIZO','max_usd':'1'},headers={'origin':'https://other.example'})
    assert blocked.status_code==403
print('Archive protected; new experiments isolated; no API spending.')
'''
    result=subprocess.run([sys.executable,'-c',code],cwd=root,env=env,capture_output=True,text=True,timeout=90)
    assert result.returncode==0,result.stdout+result.stderr
    # A fresh process and work directory represent a free-instance restart.
    env['EVALIA_WORK_DIR']=str(tmp_path/'after_restart')
    restart='''
from fastapi.testclient import TestClient
from backend.render_app import create_app
with TestClient(create_app()) as c:
    assert c.get('/api/experiments').json()['total']==1
    assert c.get('/api/experiments/108/results').json()['results'][0]['response_text']=='Respuesta simulada'
'''
    result=subprocess.run([sys.executable,'-c',restart],cwd=root,env=env,capture_output=True,text=True,timeout=90)
    assert result.returncode==0,result.stdout+result.stderr

def test_cloud_never_loads_windows_credential(monkeypatch,tmp_path):
    from backend import luna_credentials
    credential=tmp_path/'key.dpapi';credential.write_text('local encrypted credential')
    monkeypatch.setattr(luna_credentials,'FILE',credential)
    monkeypatch.setenv('EVALIA_CLOUD_RUNTIME_ROOT',str(tmp_path))
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    assert not luna_credentials.available() and not luna_credentials.load()
