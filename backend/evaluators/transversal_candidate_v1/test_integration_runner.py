import asyncio,json
from copy import deepcopy
import pytest
from .integration_runner import IntegrationRunner,create_app,aggregate_v2,connect_backend
from .test_routes import reader,bad_codes,originals,Provider

def record(rubric):
    return dict(rubric_type=rubric,turn=1,model='control',conversation='route-test',originals=[vars(r) for r in originals])

def http(runner,method='POST',path='/api/responses/1/evaluate'):
    messages=[]
    async def receive(): return dict(type='http.request',body=b'')
    async def send(x): messages.append(x)
    # In-process ASGI exchange: send/receive complete immediately. Avoid an
    # event loop self-pipe, which the strict offline network guard forbids.
    request=create_app(runner)(dict(type='http',method=method,path=path),receive,send)
    try: request.send(None)
    except StopIteration: pass
    else: raise AssertionError('Unexpected asynchronous I/O in isolated fixture route')
    return messages[0]['status'],json.loads(messages[1]['body'])

@pytest.fixture(scope='module')
def baseline():
    return http(IntegrationRunner(lambda _:record('ansiedad_depresion'),anxiety_reader=reader()))[1]

@pytest.mark.parametrize('code',bad_codes)
@pytest.mark.parametrize('role',['extract','independent_verify'])
def test_http_all_38_faults_preserve_neighbors(code,role,baseline,monkeypatch):
    from backend.evaluators.ansiedad_candidate_v3 import engine as old
    monkeypatch.setattr(old,'evaluate_turn',lambda *a,**k: (_ for _ in ()).throw(AssertionError('old engine selected')))
    status,result=http(IntegrationRunner(lambda _:record('ansiedad_depresion'),anxiety_reader=reader(code,17,role)))
    assert status==200 and 'ISOLATION' in result['engine']
    a={r['code']:r for r in baseline['indicator_results']};b={r['code']:r for r in result['indicator_results']}
    assert b[code]['status']=='BLOCKED' and b[code]['score'] is None
    assert all(a[c]==b[c] for c in a if c!=code)
    assert result['aggregation']['global_v2'] is None

def test_http_crisis_executes_final_v3_and_F2():
    p=Provider(flag=False)
    status,result=http(IntegrationRunner(lambda _:record('crisis'),crisis_provider=p))
    assert status==200 and len(result['indicator_results'])==104
    assert all(r['status']=='BLOCKED' for r in result['indicator_results'] if r['code']!='CR-CE10')
    assert next(r for r in result['indicator_results'] if r['code']=='CR-NI6')['technical_cause']=='incomplete_context_review'
    defs={k:v for _,content in p.calls for k,v in content['predicates'].items()}
    assert 'No atribuyas precisión' in defs['CR-NI6.c']['text']
    assert 'NO demuestran reconocimiento' in defs['CR-NI6.a']['text']
    assert 'Un reconocimiento genérico de necesitar ayuda' in defs['CR-NI6.b']['text']
    assert result['aggregation']['global_v2'] is None

def test_http_preserves_authoritative_temporal_context():
    r=record('crisis');r['originals'].append(dict(conversation='route-test',model='control',turn=2,user='FUTURO',response='FUTURO'))
    p=Provider()
    http(IntegrationRunner(lambda _:r,crisis_provider=p))
    assert all('FUTURO' not in json.dumps(c) for _,c in p.calls)

def test_http_fail_closed_without_provider():
    assert http(IntegrationRunner(lambda _:record('crisis')))[0]==503
    assert http(IntegrationRunner(lambda _:record('crisis')),method='GET')[0]==405

def test_V2_and_allNA_and_incomplete():
    inv={'A':'one','B':'two','C':'two'}
    rows=[dict(code=c,status='SCORED',score=s) for c,s in [('A',3),('B',0),('C',0)]]
    assert aggregate_v2(rows,inv)['global_v2']==50
    assert aggregate_v2(rows[:-1],inv)['global_v2'] is None
    assert aggregate_v2([dict(code=c,status='N/A',score=None) for c in inv],inv)['global_v2'] is None

@pytest.mark.parametrize('case,score,status',[('generic',1,'SCORED'),('imprecise',None,'BLOCKED')])
def test_http_routes_real_official_NI6_claims(case,score,status):
    from pathlib import Path
    root=Path('docs/final_repair_20261014/integration_final_05')
    contexts=json.loads(Path('docs/crisis_adjudication_20261014/step3_04/cases.json').read_text(encoding='utf-8'))
    c=next(r for r in contexts if r['id']==case)
    claims={}
    for stage in ('extract','verify'):
        path=root/('generic_fix_'+stage+'_claims.json') if case=='generic' else Path('docs/crisis_adjudication_20261014/step3_06')/('imprecise_'+stage+'_claims.json')
        claims[stage]=json.loads(path.read_text(encoding='utf-8'))
    class RealSavedNI6:
        def run(self,stage,system,content,schema,ids,identity):
            own={r['id']:r for r in claims[stage]['claims']}
            return dict(reviewed_entire_context=True,claims=[deepcopy(own[k]) if k in own else dict(id=k,state='unknown',citations=[],reason='Other indicators not read in this focal recorded evidence test.') for k in ids])
    r=dict(rubric_type='crisis',turn=1,model='NI6-official-focal',conversation='focal-recorded',originals=[dict(conversation='focal-recorded',model='NI6-official-focal',turn=1,user=c['user'],response=c['ai'])])
    http_status,result=http(IntegrationRunner(lambda _:r,crisis_provider=RealSavedNI6()))
    actual=next(r for r in result['indicator_results'] if r['code']=='CR-NI6')
    assert http_status==200 and (actual['score'],actual['status'])==(score,status)
    assert actual['verified_decisions']['CR-NI6.c']['extraction']==next(r for r in claims['extract']['claims'] if r['id']=='CR-NI6.c')
    assert result['aggregation']['global_v2'] is None

def test_current_backend_context_bridge_preserves_snapshot_guard():
    from backend.evaluators.evaluation_context import EvaluationContext,ConversationTurn
    events=[]
    raw=dict(experiment_id=999,scenario_code='synthetic',scenario_id=123,turn_number=1,model_name='control')
    def lookup(response_id): events.append(('lookup',response_id));return raw
    def guard(*args): events.append(('snapshot',args))
    def build(r):
        events.append(('build',r))
        return EvaluationContext(999,'synthetic','crisis','control',[ConversationTurn(1,'texto','texto')])
    app=connect_backend(get_response_context=lookup,build_evaluation_context=build,require_snapshot_current=guard,crisis_provider=Provider(flag=False))
    messages=[]
    async def receive(): return dict(type='http.request',body=b'')
    async def send(x): messages.append(x)
    request=app(dict(type='http',method='POST',path='/api/responses/7/evaluate'),receive,send)
    try: request.send(None)
    except StopIteration: pass
    assert [x[0] for x in events]==['lookup','snapshot','build']
    result=json.loads(messages[1]['body'])
    assert messages[0]['status']==200 and result['response_id']==7
    assert 'B-CORRESPONDENCE-FIX' in result['engine']
