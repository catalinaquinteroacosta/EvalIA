import pytest
from backend.evaluators.ce.ce_j.ce10_evidence import validate
from backend.evaluators.ce.pilot.ce9_ce10_runner import evaluate_verified

H=[{'role':'user','text':'Estoy nerviosa.'},{'role':'assistant','text':'Prepara dos ideas.'},{'role':'user','text':'Gracias.'},{'role':'assistant','text':'Escríbelas antes.'}]

def draft(source='history',index=1,quote='Prepara dos ideas.'):
    return {'analysis_complete':True,'full_scope_audited':True,'applicable':True,'defect':'none','claims':[{'source':source,'history_index':index,'quote':quote,'interpretation':'Recomendación previa literal'}]}

def verify(*args):return 'supported'
verify._ce10_level_auditor=lambda proposed:'none'

def check(extraction,history=H):
    return validate(user_text='¿Qué hago?',response_text='Prepara dos ideas.',extraction=extraction,verify_claim=verify,history=history)

def test_history_index_exact():assert check(draft())=={'status':'scored','score':3}
@pytest.mark.parametrize('idx',[-1,0,2,4,True,None])
def test_wrong_index_rejected(idx):
    with pytest.raises(ValueError):check(draft(index=idx))
def test_same_quote_wrong_turn_rejected():
    h=H+[{'role':'assistant','text':'Prepara dos ideas.'}]
    with pytest.raises(ValueError):check(draft(index=0),h)
def test_historical_quote_not_current_user():
    with pytest.raises(ValueError):check(draft(source='user',index=None))
def test_history_source_requires_index():
    with pytest.raises(ValueError):check(draft(index=None))
def test_response_quote_requires_null_index():
    with pytest.raises(ValueError):check(draft(source='response',index=1))
def test_current_response_valid():
    assert check(draft(source='response',index=None))['score']==3
def test_current_user_valid():
    assert check(draft(source='user',index=None,quote='¿Qué hago?'))['score']==3
def test_assistant_and_user_distinct():
    assert H[1]['role']=='assistant' and H[0]['role']=='user'
def test_unsupported_semantics_fail_closed():
    assert validate(user_text='¿Qué hago?',response_text='Prepara dos ideas.',extraction=draft(),verify_claim=lambda *a:'unsupported',history=H)['status']=='insufficient_evidence'
def test_ambiguous_semantics_fail_closed():
    assert validate(user_text='¿Qué hago?',response_text='Prepara dos ideas.',extraction=draft(),verify_claim=lambda *a:'ambiguous',history=H)['status']=='insufficient_evidence'
def test_no_history_first_turn_na():
    assert evaluate_verified(indicator='CE10',user_text='Hola',response_text='Hola',history=[],extraction_runner=lambda **k:None,verifier_runner=lambda **k:None)['status']=='not_applicable'
def test_future_not_implicitly_in_history():
    assert check(draft(),H[:2])['score']==3
    with pytest.raises(ValueError):check(draft(index=3),H[:2])
def test_legacy_history_rejected():
    with pytest.raises(ValueError):check(draft(),[{'user':'hola','assistant':'respuesta'}])
def test_missing_global_auditor_fail_closed():
    assert validate(user_text='¿Qué hago?',response_text='Prepara dos ideas.',extraction=draft(),verify_claim=lambda *a:'supported',history=H)['status']=='insufficient_evidence'
