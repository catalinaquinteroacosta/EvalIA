import pytest
from backend.evaluators.ce.ce_d.ce4_scoring import score_ce4,ContractError
from backend.evaluators.ce.ce_d.ce4_evidence import validate_ce4_evidence

@pytest.mark.parametrize('impact,expected',list(zip(('functional', 'secondary', 'substantial', 'unusable'),[3,2,1,0])))
def test_levels(impact,expected):
    assert score_ce4(analysis_complete=True,semantic_verified=True,structure_impact=impact)['score']==expected

def test_pending():
    assert score_ce4(analysis_complete=False,semantic_verified=True,structure_impact='functional')['score'] is None

def test_unverified():
    assert score_ce4(analysis_complete=True,semantic_verified=False,structure_impact='functional')['score'] is None

def test_invalid():
    with pytest.raises(ContractError): score_ce4(analysis_complete=True,semantic_verified=True,structure_impact='unknown')

def data(quote='Claro',impact='functional'):
    return dict(analysis_complete=True,full_response_audited=True,applicable=True,applicability_evidence=dict(source='response',quote='Claro',interpretation='Extensión requiere estructura visual'),rubric_execution='clear_contextual_verifiable',claims=[dict(source='response',quote=quote,interpretation='Afirmación contextual')])

def evaluate(extraction,verifier=lambda *_:'supported'):
    return validate_ce4_evidence(user_text='Necesito ayuda',response_text='Claro, te ayudo',extraction=extraction,verify_claim=verifier)

def test_verified(): assert evaluate(data())['score']==3

def test_invalid_literal():
    result = evaluate(data('cita inventada'))
    assert result == {
        'status': 'insufficient_evidence',
        'score': None,
    }

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
    with pytest.raises(ContractError):score_ce4(analysis_complete=1,semantic_verified=True,structure_impact='functional')

def test_not_applicable():
    assert score_ce4(analysis_complete=True,semantic_verified=True,structure_impact='functional',applicable=False)['status']=='not_applicable'
    d=data();d['applicable']=False
    assert evaluate(d)['status']=='not_applicable'
