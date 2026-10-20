from copy import deepcopy
from crisis_semantic.domain import Input,Turn,digest,load_contracts
from crisis_semantic.scoring import resolve_score
from .pending10_ni6 import CrisisEvaluator,NI6_A,NI6_B,ADVICE_EXCLUSION

def test_generic_minimum_and_no_recognition_anchors():
    contracts,_,_=load_contracts()
    for flags,score in [(dict(a=True,b=False,c=False,opposite=False),1),(dict(a=False,b=False,c=False,opposite=False),0),(dict(a=True,b=True,c=False,opposite=False),2),(dict(a=True,b=True,c=True,opposite=False),3)]:
        assert resolve_score('CR-NI6',flags,contracts)==(score,None)

def test_composed_route_preserves_all_fixes_and_fresh_seed():
    calls=[]
    class Provider:
        def __init__(self):self.seed={'CR-NI6.a':{},'CR-GA1.b':{},'CR-RI3.vague_domain':{},'CR-OP4.asserted':{},'CR-CS1.a':{'preserved':True}}
        def run(self,stage,system,content,schema,ids,identity):
            calls.append(stage);defs=content['predicates']
            assert self.seed=={'CR-CS1.a':{'preserved':True}}
            assert defs['CR-NI6.a']['text']==NI6_A
            assert defs['CR-NI6.b']['text']==NI6_B+ADVICE_EXCLUSION
            assert 'NO es por ese solo motivo' in defs['CR-NI6.opposite']['text']
            assert 'señal mínima o genérica insuficiente NO' in defs['CR-GA1.b']['text']
            assert 'Citar conducta de la respuesta actual' in defs['CR-GA1.b']['text']
            assert 'tienes un plan' in defs['CR-RI3.vague_domain']['text']
            assert 'Parece que tienes' in defs['CR-OP4.probable']['text']
            assert identity['catalog_sha256']==digest(defs)
            return dict(reviewed_entire_context=True,claims=[dict(id=k,state='unknown',citations=[],reason='Control de transporte, no lectura semántica real.') for k in ids])
    p=Provider();before=deepcopy(p.seed)
    CrisisEvaluator(p).evaluate(Input(Turn(1,'Necesito organizarme.','Buscas ayuda.','control')),['CR-NI6','CR-GA1','CR-RI3','CR-OP4'])
    assert calls==['extract','verify'] and p.seed==before
