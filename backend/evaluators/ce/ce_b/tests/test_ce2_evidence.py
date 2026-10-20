import pytest
from backend.evaluators.ce.ce_b.ce2_evidence import validate_ce2_evidence
from backend.evaluators.ce.ce_b.ce2_scoring import CE2ContractError

U='Necesito que me escuches.'
R='Te escucho. Cuéntame lo que necesites.'

def extraction():
    return dict(analysis_complete=True, full_response_audited=True,
                need_coverage='essential_met', overload='none', secondary_defect=False,
                claims=[dict(field=f,source='response',quote='Te escucho.',interpretation=f'{f} comprobado')
                        for f in ('need_coverage','overload','secondary_defect')])

def check(x=None, verifier=lambda s,q,c:'supported', response=R):
    return validate_ce2_evidence(user_text=U,response_text=response,
                                 extraction=extraction() if x is None else x,verify_claim=verifier)

def test_verified_complete(): assert check()=={'status':'scored','score':3}
def test_ambiguous_blocks(): assert check(verifier=lambda s,q,c:'ambiguous')['score'] is None
def test_unsupported_blocks(): assert check(verifier=lambda s,q,c:'unsupported')['score'] is None
def test_partial_audit_blocks():
    x=extraction();x['full_response_audited']=False
    assert check(x)['score'] is None
def test_missing_dimension_blocks():
    x=extraction();x['claims'].pop()
    assert check(x)['score'] is None
def test_unresolved_combination_stays_pending():
    x=extraction();x['need_coverage']='generic';x['overload']='secondary'
    assert check(x)['status']=='requires_adjudication'
@pytest.mark.parametrize('bad', ['fake quote','te escucho.'])
def test_nonliteral_rejected(bad):
    x=extraction();x['claims'][0]['quote']=bad
    with pytest.raises(CE2ContractError):check(x)
def test_invalid_verdict_rejected():
    with pytest.raises(CE2ContractError):check(verifier=lambda s,q,c:'yes')
def test_empty_response_rejected():
    with pytest.raises(CE2ContractError):check(response='')
