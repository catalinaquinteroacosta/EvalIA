"""Offline Batch lifecycle guards; no API, shared SQLite or semantic claim."""
import json
from decimal import Decimal
from hashlib import sha256
import pytest
from backend.luna_application import PrivateBatchQueue,BatchPending,request_key


def body():return dict(model='gpt-6-luna',input='Controlled plumbing fixture',max_output_tokens=100)


def test_planning_is_idempotent_and_endpoint_alias_cannot_duplicate(tmp_path):
    queue=PrivateBatchQueue(tmp_path)
    for endpoint in ('responses','/v1/responses'):
        with pytest.raises(BatchPending):queue(body(),endpoint)
    assert len(list(tmp_path.glob('*.request.json')))==1
    manifest=queue.manifest(lambda body,mode:Decimal('0.01'))
    assert manifest['request_count']==1 and manifest['reserve_usd']=='0.01'
    assert manifest['submission_authorized'] is False


def test_exact_import_and_replay_preserve_identity_and_refuse_replacement(tmp_path):
    queue=PrivateBatchQueue(tmp_path)
    with pytest.raises(BatchPending):queue(body(),'responses')
    key,wire=request_key(body(),'responses');digest=sha256(wire).hexdigest()
    raw={'model':'gpt-6-luna','status':'completed','output':[]}
    with pytest.raises(ValueError,match='identity'):queue.import_result(key,raw,request_sha256='wrong',batch_id='batch_fixture',custom_id='one',provenance=provenance(tmp_path,body(),raw))
    queue.import_result(key,raw,request_sha256=digest,batch_id='batch_fixture',custom_id='one',provenance=provenance(tmp_path,body(),raw))
    assert queue(body(),'responses')==raw
    assert not queue.pending
    with pytest.raises(ValueError,match='provenance|required|response|overwrite'):queue.import_result(key,{**raw,'status':'incomplete'},request_sha256=digest,batch_id='batch_fixture',custom_id='one')


def test_tampered_replay_is_blocked(tmp_path):
    queue=PrivateBatchQueue(tmp_path)
    with pytest.raises(BatchPending):queue(body(),'responses')
    key,wire=request_key(body(),'responses')
    queue.import_result(key,{'model':'gpt-6-luna'},request_sha256=sha256(wire).hexdigest(),batch_id='batch_fixture',custom_id='one',provenance=provenance(tmp_path,body(),{'model':'gpt-6-luna'}))
    (tmp_path/(key+'.result.json')).write_text('{}',encoding='utf-8')
    with pytest.raises(ValueError,match='integrity'):queue(body(),'responses')


def test_other_model_and_unknown_endpoint_rejected_before_planning(tmp_path):
    queue=PrivateBatchQueue(tmp_path)
    with pytest.raises(ValueError):queue({**body(),'model':'gpt-4.1'},'responses')
    with pytest.raises(ValueError):queue(body(),'batches')
    assert list(tmp_path.iterdir())==[]


def test_real_http_evaluation_pending_does_not_persist_or_spend(tmp_path,monkeypatch):
    """Actual frontend POST route with controlled transport, no semantic claim."""
    import asyncio
    from fastapi import HTTPException
    from backend import main,integrated_evaluation
    queue=PrivateBatchQueue(tmp_path)
    def absent(_):raise HTTPException(status_code=404,detail='fixture absent')
    monkeypatch.setattr(main,'_get_response_context',lambda _:dict(experiment_id=900001,scenario_code='CONTROLLED TEST FIXTURE',scenario_id=900001))
    monkeypatch.setattr(main,'_load_saved_evaluation',absent)
    monkeypatch.setattr(main,'_require_experiment_snapshot_current',lambda *args:None)
    monkeypatch.setattr(integrated_evaluation,'authoritative_record',lambda *args:dict(rubric_type='crisis'))
    # This controlled fixture has no persisted manual review. Its lookup is a
    # separate read boundary, not part of this pending-transport test.
    monkeypatch.setattr(integrated_evaluation,'load_review',lambda *args:None)
    def forbidden(*args,**kwargs):raise AssertionError('Pending Batch must not persist or open SQLite')
    monkeypatch.setattr(main,'get_connection',forbidden)
    monkeypatch.setattr(main,'_save_evaluation_result',forbidden)
    class ControlledRunner:
        def __init__(self,*args,**kwargs):pass
        def evaluate_response(self,_):return queue(body(),'responses')
    monkeypatch.setattr(main.app.state,'evaluation_dependencies',dict(crisis_provider=object(),runner_factory=ControlledRunner,
        allowed_experiment_ids={900001}),raising=False)
    async def post():
        events=[]
        async def receive():return dict(type='http.request',body=b'',more_body=False)
        async def send(event):events.append(event)
        await main.app(dict(type='http',asgi={'version':'3.0'},http_version='1.1',method='POST',scheme='http',
            path='/api/responses/900001/evaluate',raw_path=b'/api/responses/900001/evaluate',query_string=b'',
            root_path='',headers=[],server=('127.0.0.1',0),client=('127.0.0.1',1)),receive,send)
        return events
    for _ in range(2):
        events=asyncio.run(post())
        assert next(e for e in events if e['type']=='http.response.start')['status']==202
        payload=json.loads(b''.join(e.get('body',b'') for e in events if e['type']=='http.response.body'))
        assert payload.get('status')=='batch_pending' or payload.get('detail',{}).get('status')=='batch_pending'
    assert len(list(tmp_path.glob('*.request.json')))==1


@pytest.mark.parametrize('rubric',[ 'crisis','ansiedad_depresion'])
def test_complete_family_planning_collects_independent_readers_before_pending(tmp_path,rubric):
    if rubric == 'ansiedad_depresion':
        from backend.evaluators.ansiedad_candidate_v3.engine import FROZEN
        if not (FROZEN / 'FREEZE.json').is_file():
            pytest.skip('Historical sealed release is local research evidence, not distributed in Git.')
    from backend.luna_runner import dependencies
    queue=PrivateBatchQueue(tmp_path)
    deps=dependencies(queue,allowed_experiment_ids=[900001])
    record=dict(rubric_type=rubric,model='CONTROLLED FIXTURE MODEL',turn=1,conversation='900001:CONTROLLED',
        originals=[dict(conversation='900001:CONTROLLED',model='CONTROLLED FIXTURE MODEL',turn=1,
            user='Estoy preocupado por la presentación. Estoy a salvo.',response='Puedo escucharte. ¿Qué parte te preocupa?')])
    runner=deps['runner_factory'](lambda _:record,crisis_provider=deps['crisis_provider'],anxiety_reader=deps['anxiety_reader'])
    with pytest.raises(BatchPending):runner.evaluate_response(900001)
    manifest=queue.manifest(lambda body,mode:Decimal('0.01'))
    assert manifest['request_count']>=2
    stages=[]
    for row in manifest['requests']:
        body=row['body']
        assert body['model']=='gpt-6-luna'
        content=json.loads(body['input'][1]['content'] if 'input' in body else body['messages'][1]['content'])
        if rubric=='ansiedad_depresion':stages.append(content['stage'])
        else:stages.append(body['input'][0]['content'])
    if rubric=='ansiedad_depresion':
        assert stages.count('extract')==stages.count('independent_verify')
    else:
        from backend.luna_reader import PROMPT,VERIFY
        # Scoped clarifications differ by package; the two independent base
        # instructions remain distinct and occur equally often.
        assert sum(s.startswith(PROMPT) and not s.startswith(VERIFY) for s in stages)==sum(s.startswith(VERIFY) for s in stages)
        assert all(s.startswith(PROMPT) or s.startswith(VERIFY) for s in stages)
    before=manifest['request_count']
    with pytest.raises(BatchPending):runner.evaluate_response(900001)
    assert queue.manifest(lambda body,mode:Decimal('0.01'))['request_count']==before


def provenance(directory,body,raw):
    """Explicit synthetic plumbing receipt; never scientific qualification evidence."""
    folder=directory/'receipt-fixture';folder.mkdir(exist_ok=True)
    req=dict(custom_id='one',method='POST',url='/v1/responses',body=body)
    row=dict(custom_id='one',error=None,response=dict(status_code=200,request_id='synthetic-request-id',body=raw))
    def write(name,value,jsonl=False):
        p=folder/name;p.write_text(json.dumps(value) if not jsonl else json.dumps(value)+'\n',encoding='utf8')
        return dict(path=str(p),sha256=sha256(p.read_bytes()).hexdigest())
    requests=write('requests.json',[req]);inp=write('input.jsonl',req,True);out=write('output.jsonl',row,True)
    execution=write('execution_fixture.json',{'controlled_fixture':True})
    manifest=write('manifest.json',[requests,inp,dict(path='backend/luna_reader.py',sha256=execution['sha256'])])
    auth=write('authorization.json',dict(explicit_user_approval=True,model='gpt-6-luna',mode='Batch',max_usd=2,max_requests=1,scope=folder.name))
    job=write('job.json',dict(id='batch_fixture',status='completed',endpoint='/v1/responses',output_file_id='synthetic-output',input_file_id='synthetic-input',request_counts={'total':1}))
    state=write('state.json',dict(jobs=[dict(batch_id='batch_fixture',file_id='synthetic-input',input_sha256=inp['sha256'],requests=1)]))
    return dict(authorization=auth,execution_adapter=execution,batch_evidence=dict(manifest=manifest,requests=requests,input=inp,output=out,job=job,state=state),request=req,response=row,synthetic_fixture=True)


def test_bare_batch_ids_do_not_authorize_import(tmp_path):
    queue=PrivateBatchQueue(tmp_path)
    with pytest.raises(BatchPending):queue(body(),'responses')
    key,wire=request_key(body(),'responses')
    with pytest.raises(ValueError,match='provenance_required'):
        queue.import_result(key,{'model':'gpt-6-luna'},request_sha256=sha256(wire).hexdigest(),batch_id='batch_fixture',custom_id='one')


def test_two_processes_plan_one_original(tmp_path):
    import subprocess,sys,os
    script="from backend.luna_application import PrivateBatchQueue,BatchPending; import sys; q=PrivateBatchQueue(sys.argv[1]); b=dict(model='gpt-6-luna',input='controlled',max_output_tokens=100);\nfor i in range(12):\n try:q(b,'responses')\n except BatchPending:pass"
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}
    ps=[subprocess.Popen([sys.executable,'-B','-c',script,str(tmp_path)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE) for _ in range(2)]
    for p in ps:
        stdout,stderr=p.communicate(timeout=30)
        assert p.returncode==0,stderr.decode(errors='replace')
    assert len(list(tmp_path.glob('*.request.json')))==1


def test_real_downloaded_batch_import_retains_receipt_chain(tmp_path):
    from tests.test_luna_qualification import bundle,BASE
    if not (BASE / 'execution_v2/AUTHORIZATION.json').is_file():
        pytest.skip('Requires private original batch receipts; no synthetic replacement is permitted.')
    proof,req,response,reading=bundle()
    raw=response['response']['body']
    q=PrivateBatchQueue(tmp_path)
    with pytest.raises(BatchPending):q(req['body'],req['url'])
    key,wire=request_key(req['body'],req['url'])
    provenance={**proof,'request':req,'response':response}
    q.import_result(key,raw,request_sha256=sha256(wire).hexdigest(),batch_id=reading['batch_id'],custom_id=reading['custom_id'],provenance=provenance)
    assert q(req['body'],req['url'])==raw
    bad={**req['body'],'max_output_tokens':req['body']['max_output_tokens']+1}
    with pytest.raises(BatchPending):q(bad,req['url'])
    badkey,badwire=request_key(bad,req['url'])
    with pytest.raises(ValueError,match='original_request'):
        q.import_result(badkey,raw,request_sha256=sha256(badwire).hexdigest(),batch_id=reading['batch_id'],custom_id=reading['custom_id'],provenance=provenance)


def test_review_persistence_is_idempotent_with_native_tuple_audit(tmp_path):
    import sqlite3
    from types import SimpleNamespace
    from concurrent.futures import ThreadPoolExecutor
    from backend.integrated_evaluation import save_review
    path=tmp_path/'private.db'
    def connect():
        c=sqlite3.connect(path,timeout=10);c.row_factory=sqlite3.Row;return c
    with connect() as c:c.execute('CREATE TABLE responses(id INTEGER PRIMARY KEY)');c.execute('INSERT INTO responses VALUES (1)')
    main=SimpleNamespace(get_connection=connect)
    public=dict(engine_version='controlled-test',evaluation_state='review_required',audit={'tuple':('preserve',None)})
    with ThreadPoolExecutor(max_workers=2) as pool:
        ids=list(pool.map(lambda _:save_review(main,1,public),range(2)))
    assert ids[0]==ids[1]
    with connect() as c:
        assert c.execute('SELECT COUNT(*) FROM evaluation_reviews').fetchone()[0]==1
        saved=json.loads(c.execute('SELECT result_json FROM evaluation_reviews').fetchone()[0])
        assert saved['audit']['tuple']==['preserve',None]
