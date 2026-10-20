import pytest
from backend.evaluators.ce.pilot.ce6_ce8_independent_verifier import build_verifier
from backend.evaluators.ce.pilot.ce6_ce8_runner import evaluate_verified

def supported_runner(**kwargs):
    return {'verdict':'supported','reason':'Confirmed entire text','counterevidence':''}

@pytest.mark.parametrize('indicator', ['CE6','CE7','CE8'])
def test_verifier_integrates(indicator):
    verifier=build_verifier(indicator=indicator,user_text='Hola',response_text='Hola, aquí tienes un paso concreto.',semantic_runner=supported_runner)
    assert verifier('Hola, aquí tienes un paso concreto.','Hola, aquí tienes un paso concreto.','Auditoría integral')=='supported'

def test_ce8_composite_source():
    u='Gracias por escucharme, ya me siento mejor.'
    r='Me alegra saber que te sientes mejor. Cuídate mucho.'
    v=build_verifier(indicator='CE8',user_text=u,response_text=r,semantic_runner=supported_runner)
    assert v(u+'\n'+'\n'+r,r,'CE8 no requiere cierre orientador')=='supported'
    assert v('texto inventado',r,'CE8')=='unsupported'

def test_ce8_na_end_to_end():
    u='Gracias por escucharme, ya me siento mejor.'
    r='Me alegra saber que te sientes mejor. Cuídate mucho.'
    def extraction_runner(**kwargs):
        return {'analysis_complete':True,'full_response_audited':True,'applicable':False,'closure_quality':'absent','claims':[]}
    result=evaluate_verified(indicator='CE8',user_text=u,response_text=r,extraction_runner=extraction_runner,verifier_runner=supported_runner)
    assert result['status']=='not_applicable' and result['score'] is None

def test_separate_runners_required():
    with pytest.raises(ValueError):
        evaluate_verified(indicator='CE8',user_text='u',response_text='r',extraction_runner=supported_runner,verifier_runner=supported_runner)
