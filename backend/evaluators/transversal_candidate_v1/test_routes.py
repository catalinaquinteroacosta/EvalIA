"""Candidate integration regression with controlled readers, never providers."""
import sys,json
from pathlib import Path
from copy import deepcopy
sys.path.insert(0,str(Path('backend/evaluators').resolve()))
import pytest
from backend.evaluators.transversal_candidate_v1 import anxiety
from backend.evaluators.transversal_candidate_v1.crisis import CrisisEvaluator,reconcile_complete
from backend.evaluators.ansiedad_semantic.identified_context import OriginalTurn,authorized_context
from backend.evaluators.ansiedad_candidate_v3.engine import evaluate_turn as old_engine
from crisis_semantic.domain import load_contracts,Input,Turn
from crisis_semantic.predicate_catalog import definitions
from crisis_semantic.evidence import EvidenceError

BASE=Path('docs/final_transversal_20261014/run_01')
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
truth=read(BASE/'truth_tables.json')
witness={r['code']:r['witnesses'].get('3',{}) for r in truth if r['engine']=='ANSIEDAD'}
bad_codes=[r['code'] for r in read(BASE/'protocol_controls.json') if r.get('result')=='ERROR:AttributeError']
originals=[OriginalTurn('route-test','control',1,'texto','texto')]
identified=authorized_context(originals,'route-test','control',1)
def reader(target=None,value=None,role=None,mode='reason'):
    def callback(q):
        payload={'indicators':{c:{'components':{k:{'value':witness[c].get(k,False),
          'evidence':[{'source':'user','quote':'texto','history_index':None},{'source':'response','quote':'texto','history_index':None}] if witness[c].get(k,False) else [],
          'counterevidence':[],'complete_response_reviewed':True,'reason':'Control explícito, no interpretación semántica certificada.'} for k in d['components']}} for c,d in q['indicators'].items()}}
        if target in payload['indicators'] and (role is None or q['stage']==role):
            if mode=='missing':del payload['indicators'][target]
            elif mode=='reason':payload['indicators'][target]['components'][next(iter(payload['indicators'][target]['components']))]['reason']=value
            elif mode=='citation':payload['indicators'][target]['components'][next(iter(payload['indicators'][target]['components']))]['evidence']=[{'source':'response','quote':'INVENTADO','history_index':None}]
            elif mode=='review':payload['indicators'][target]['components'][next(iter(payload['indicators'][target]['components']))]['complete_response_reviewed']=False
        return payload
    return callback

@pytest.mark.parametrize('code',bad_codes)
@pytest.mark.parametrize('role',['extract','independent_verify'])
@pytest.mark.parametrize('value',[17,None,{},[],'','  '])
def test_actual_family_isolates_every_bad_reason(code,role,value):
    family=code[:2]
    baseline=anxiety.run_family(identified,family,reader=reader())['results']
    current=anxiety.run_family(identified,family,reader=reader(code,value,role))['results']
    assert baseline[code]['status']=='SCORED'
    assert current[code]['status']=='BLOCKED' and current[code]['score'] is None
    assert all(current[c]==baseline[c] for c in baseline if c!=code)
    if not isinstance(value,str):assert current[code]['reason'].startswith('invalid_reason_type:')

@pytest.mark.parametrize('code',bad_codes)
@pytest.mark.parametrize('mode',['missing','citation','review'])
def test_other_indicator_faults_are_contained(code,mode):
    family=code[:2];old=anxiety.run_family(identified,family,reader=reader())['results']
    new=anxiety.run_family(identified,family,reader=reader(code,mode=mode))['results']
    assert new[code]['status']=='BLOCKED'
    assert all(new[c]==old[c] for c in old if c!=code)

def test_real_full_engine_IR2_preserves_IR1_and_all_neighbors():
    old=anxiety.evaluate_turn(originals,'route-test','control',1,reader=reader())
    new=anxiety.evaluate_turn(originals,'route-test','control',1,reader=reader('IR2',17))
    a={r['code']:r for r in old['rows']};b={r['code']:r for r in new['rows']}
    assert a['IR1']['status']==b['IR1']['status']=='SCORED'
    assert b['IR2']['status']=='BLOCKED'
    assert all(a[c]==b[c] for c in a if c!='IR2')

def test_full_valid_engine_matches_frozen_decisions():
    a=old_engine(originals,'route-test','control',1,reader=reader())
    b=anxiety.evaluate_turn(originals,'route-test','control',1,reader=reader())
    for x,y in zip(a['rows'],b['rows']):
        assert {k:v for k,v in x.items() if k!='engine_version'}=={k:v for k,v in y.items() if k!='engine_version'}

def test_reader_mutation_does_not_contaminate_independent_payload():
    seen=[];valid=reader()
    def mutate(q):
        seen.append(deepcopy(q));result=valid(q);q['original']['response']='CAMBIADO';return result
    anxiety.run_family(identified,'IR',reader=mutate)
    assert seen[0]['original']==seen[1]['original'] and seen[1]['original']['response']=='texto'

class Provider:
    qualified_components={'CR-RI2','CR-CE10'}
    def __init__(self,flag=True,gate=True):self.flag=flag;self.gate=gate;self.calls=[]
    def run(self,stage,system,content,schema,ids,identity):
        self.calls.append((stage,deepcopy(content)))
        claims=[]
        for key,d in content['predicates'].items():
            present=self.gate if key.endswith('.gate') else (not key.endswith('.opposite'))
            claims.append({'id':key,'state':'yes' if present else 'no','citations':[{'source':'current_user' if d['kind']=='gate' else 'current_ai','history_index':None,'quote':'texto'}] if present else [],'reason':'Hecho controlado.'})
        return {'reviewed_entire_context':self.flag,'claims':claims}

@pytest.mark.parametrize('code',list(load_contracts()[0]))
def test_crisis_incomplete_context_is_never_adjudicated(code):
    p=Provider(False);result=CrisisEvaluator(p).evaluate(Input(Turn(1,'texto','texto','control')),[code])
    row=result['results'][0]
    if code=='CR-CE10':
        assert row['status']=='N/A' and row['score'] is None
    else:
        assert row['status']=='BLOCKED'
        assert row['technical_cause']=='incomplete_context_review'
    assert all(r['value'] is None for r in row['verified_decisions'].values())
    assert len(p.calls)==2 and p.calls[0][0]=='extract' and p.calls[1][0]=='verify'
    assert 'previous_verification_issues_to_correct_without_inventing' not in p.calls[1][1]

def test_crisis_NA_and_omission_are_distinct_with_full_review():
    ctx=Input(Turn(1,'texto','texto','control'))
    result=CrisisEvaluator(Provider(True,False)).evaluate(ctx,['CR-NI3'])['results'][0]
    assert result['status']=='N/A' and result['score'] is None
    class Omission(Provider):
        def run(self,*args):
            result=super().run(*args)
            for c in result['claims']:
                if not c['id'].endswith('.gate'):c.update(state='no',citations=[])
            return result
    result=CrisisEvaluator(Omission(True,True)).evaluate(ctx,['CR-NI3'])['results'][0]
    assert result['status']=='SCORED' and result['score']==0

@pytest.mark.parametrize('role',[0,1])
def test_crisis_either_reader_incomplete_rejected(role):
    ctx=Input(Turn(1,'texto','texto','control'));defs=definitions(load_contracts()[0],['CR-CS1'])
    p=Provider();content={'predicates':defs};a=p.run('extract','',content,None,None,None);b=deepcopy(a)
    [a,b][role]['reviewed_entire_context']=False
    with pytest.raises(EvidenceError):reconcile_complete(a,b,defs,ctx)

@pytest.mark.parametrize('code',list(load_contracts()[0]))
def test_crisis_complete_valid_pair_keeps_frozen_decision(code):
    from crisis_semantic.pipeline import CrisisEvaluator as Frozen
    ctx=Input(Turn(1,'texto','texto','control'))
    assert CrisisEvaluator(Provider()).evaluate(ctx,[code])==Frozen(Provider(),recovery=False).evaluate(ctx,[code])

def test_NA_ignores_unrequired_malformed_reason_without_false_BLOCKED():
    valid=reader()
    def inactive(q):
        result=valid(q)
        r=result['indicators']['PA3']['components'];r['gate_present']['value']=False;r['gate_present']['evidence']=[]
        name=next(k for k in r if k!='gate_present');r[name]['reason']=17
        return result
    result=anxiety.run_family(identified,'PA',reader=inactive)['results']
    assert result['PA3']['status']=='N/A' and result['PA3']['score'] is None

def test_crisis_temporal_gate_active_stays_BLOCKED_when_review_incomplete():
    ctx=Input(Turn(3,'texto','texto','control'),(Turn(1,'texto','texto','control'),Turn(2,'texto','texto','control')))
    r=CrisisEvaluator(Provider(False)).evaluate(ctx,['CR-CE10'])['results'][0]
    assert r['status']=='BLOCKED' and r['technical_cause']=='incomplete_context_review'

def test_crisis_extractor_mutation_does_not_reach_verifier():
    class Mutating(Provider):
        def run(self,stage,system,content,schema,ids,identity):
            result=super().run(stage,system,content,schema,ids,identity)
            content['conversation']['current_ai']='CAMBIADO'
            return result
    p=Mutating();CrisisEvaluator(p).evaluate(Input(Turn(1,'texto','texto','control')),['CR-CS1'])
    assert p.calls[0][1]==p.calls[1][1]
    assert p.calls[1][1]['conversation']['current_ai']=='texto'

def test_reason_type_rejected_before_legacy_AttributeError(monkeypatch):
    from backend.evaluators.nd.contracts import TurnContext
    captured=[]
    def collect(q):captured.append(reader('IR2',17)(q));return captured[-1]
    anxiety.run_family(identified,'IR',reader=collect)
    a,b=[r['indicators']['IR2'] for r in captured]
    def forbidden_delegate(*a,**k):raise AssertionError('Malformed reason reached legacy adjudicator')
    monkeypatch.setattr(anxiety,'frozen_adjudicate',forbidden_delegate)
    result=anxiety.adjudicate('IR2',TurnContext('texto','texto'),a,b)
    assert result['status']=='BLOCKED' and result['reason'].startswith('invalid_reason_type:')
