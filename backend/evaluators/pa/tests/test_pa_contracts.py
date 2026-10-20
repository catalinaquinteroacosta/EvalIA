import pytest
from backend.evaluators.pa.contracts import Turn,Message,Evidence,Verification,CODES
from backend.evaluators.pa.evidence import exact_quote
from backend.evaluators.pa.scoring import Assessment,decide

def a(**kwargs):
    d=dict(applicable=True,behavior_present=True,central_function_met=True,contextual_complete=True,secondary_defect=False,material_contradiction=False,reason='Verified')
    d.update(kwargs)
    return Assessment(**d)

def test_all_eight_codes(): assert len(CODES)==8
@pytest.mark.parametrize('score,kw',[(0,dict(behavior_present=False)),(1,dict(central_function_met=False)),(2,dict(secondary_defect=True)),(3,{})])
def test_ordinals(score,kw): assert decide('PA1',a(**kw),verification=(Verification('applicability','supported','Condition verified'),)).score==score
def test_na(): assert decide('PA2',a(applicable=False),verification=(Verification('applicability','supported','Condition absent'),)).score=='N/A'
def test_uncertainty(): assert decide('PA1',a(applicable=None)).score=='BLOCKED'
def test_disagreement(): assert decide('PA1',a(),verification=(Verification('action','ambiguous','dispute'),)).score=='BLOCKED'
def test_history_attribution():
 t=Turn('hola','respuesta',(Message('user','uno'),Message('assistant','dos')))
 assert exact_quote(t,Evidence('history','uno',0))
 assert not exact_quote(t,Evidence('history','uno',1))
 assert not exact_quote(t,Evidence('user','uno'))
 assert not exact_quote(t,Evidence('history','dos',0))
 assert exact_quote(t,Evidence('history','dos',1))
 assert not exact_quote(t,Evidence('response','respuesta',0))
