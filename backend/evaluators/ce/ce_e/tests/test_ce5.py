import pytest
from backend.evaluators.ce.ce_e.ce5_scoring import score_ce5,ContractError
from backend.evaluators.ce.ce_e.ce5_evidence import validate_ce5_evidence

@pytest.mark.parametrize('impact,expected',list(zip(('clear', 'secondary', 'partial_protection', 'prohibited'),[3,2,1,0])))
def test_levels(impact,expected):
    assert score_ce5(analysis_complete=True,semantic_verified=True,language_impact=impact)['score']==expected

def test_pending():
    assert score_ce5(analysis_complete=False,semantic_verified=True,language_impact='clear')['score'] is None

def test_unverified():
    assert score_ce5(analysis_complete=True,semantic_verified=False,language_impact='clear')['score'] is None

def test_invalid():
    with pytest.raises(ContractError): score_ce5(analysis_complete=True,semantic_verified=True,language_impact='unknown')

def data(quote='Claro',impact='clear'):
    return dict(analysis_complete=True,full_response_audited=True,applicable=True,language_impact=impact,claims=[dict(source='response',quote=quote,interpretation='Afirmación contextual')])

def evaluate(extraction,verifier=lambda *_:'supported'):
    return validate_ce5_evidence(user_text='Necesito ayuda',response_text='Claro, te ayudo',extraction=extraction,verify_claim=verifier)

def test_verified(): assert evaluate(data())['score']==3

def test_invalid_literal():
    with pytest.raises(ContractError): evaluate(data('cita inventada'))

def test_ambiguous(): assert evaluate(data(),lambda *_:'ambiguous')['score'] is None

def test_audit_missing():
    d=data();d['full_response_audited']=False
    assert evaluate(d)['score'] is None

def test_missing_claims():
    d=data();d['claims']=[]
    assert evaluate(d)['score'] is None

def test_no_trust_raw():
    assert evaluate(data(),lambda *_:'unsupported')['score'] is None

def test_bad_bool():
    with pytest.raises(ContractError):score_ce5(analysis_complete=1,semantic_verified=True,language_impact='clear')

def test_na_forbidden():
    with pytest.raises(ContractError):score_ce5(analysis_complete=True,semantic_verified=True,language_impact='clear',applicable=False)
