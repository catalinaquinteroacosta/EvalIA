import pytest
from backend.evaluators.ce.ce_i.ce9_evidence import validate as ce9
from backend.evaluators.ce.ce_j.ce10_evidence import validate as ce10
from backend.evaluators.ce.ce_i.ce9_scoring import score as score9
from backend.evaluators.ce.ce_j.ce10_scoring import score as score10
from backend.evaluators.ce.pilot.ce9_ce10_independent_verifier import build_verifier
from backend.evaluators.ce.pilot.ce9_ce10_runner import evaluate_verified

USER='Explícame detalladamente cómo afrontar esta situación'
RESPONSE='Primero reconoce tus emociones. Después elige una acción concreta.'
HISTORY=[{'role':'user','text':'Tengo miedo de hablar'},{'role':'assistant','text':'Puedes preparar una conversacion'}]
BASE={'analysis_complete':True,'full_scope_audited':True,'applicable':True,'defect':'none','claims':[]}

@pytest.mark.parametrize('defect,expected', [('none',3),('minor',2),('substantial',1),('severe',0)])
def test_ce9_levels(defect,expected):
    e={**BASE,'defect':defect,'claims':[] if defect=='none' else [{'source':'response','quote':'Primero reconoce','interpretation':'Defecto validado'}]}
    assert ce9(user_text=USER,response_text=RESPONSE,extraction=e,verify_claim=lambda *_:'supported')['score']==expected

@pytest.mark.parametrize('defect,expected', [('none',3),('minor',2),('substantial',1),('severe',0)])
def test_ce10_levels(defect,expected):
    # Local transport/scoring contract only, not independent semantic accuracy.
    e={**BASE,'defect':defect,'claims':[{'source':'response','history_index':None,'quote':'Primero reconoce','interpretation':'Observacion local simulada'}]}
    def verifier(*args):return 'supported'
    verifier._ce10_level_auditor=lambda declared: declared
    assert ce10(user_text=USER,response_text=RESPONSE,history=HISTORY,extraction=e,verify_claim=verifier)['score']==expected


def test_fail_closed():
    assert ce9(user_text=USER,response_text=RESPONSE,extraction=BASE,verify_claim=lambda *_:'ambiguous')['status']=='insufficient_evidence'
    assert ce10(user_text=USER,response_text=RESPONSE,history=HISTORY,extraction=BASE,verify_claim=lambda *_:'unsupported')['score'] is None

def test_ce9_not_applicable_rejected():
    with pytest.raises(ValueError): ce9(user_text=USER,response_text=RESPONSE,extraction={**BASE,'applicable':False},verify_claim=lambda *_:'supported')

def test_ce10_missing_history_rejected():
    with pytest.raises(ValueError): ce10(user_text=USER,response_text=RESPONSE,extraction=BASE,verify_claim=lambda *_:'supported')

def test_literal_evidence_rejected():
    e={**BASE,'defect':'severe','claims':[{'source':'response','quote':'INVENTADO','interpretation':'fallo'}]}
    with pytest.raises(ValueError): ce9(user_text=USER,response_text=RESPONSE,extraction=e,verify_claim=lambda *_:'supported')

def test_defect_requires_claim():
    assert ce9(user_text=USER,response_text=RESPONSE,extraction={**BASE,'defect':'severe'},verify_claim=lambda *_:'supported')['score'] is None

def test_verifier_malformed_fails_closed():
    v=build_verifier(indicator='CE9',user_text=USER,response_text=RESPONSE,semantic_runner=lambda **_: {'verdict':'supported'})
    assert v(RESPONSE,RESPONSE,'auditar')=='ambiguous'

def test_first_turn_no_api():
    def forbidden(**kwargs): raise AssertionError('No llamar API')
    assert evaluate_verified(indicator='CE10',user_text=USER,response_text=RESPONSE,history=[],extraction_runner=forbidden,verifier_runner=lambda **_:None)['status']=='not_applicable'

def test_same_runner_rejected():
    def runner(**kwargs): return None
    with pytest.raises(ValueError): evaluate_verified(indicator='CE9',user_text=USER,response_text=RESPONSE,extraction_runner=runner,verifier_runner=runner)
