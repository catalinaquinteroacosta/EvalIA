from backend.evaluators.ps.contracts import Turn, Decision
from backend.evaluators.ps.semantic import SemanticResult
from backend.evaluators.ps.pilot_guard import audit_result, audit_family

def result(code='PS2', score=3, evidence=None, **extras):
    return SemanticResult(code, Decision(code,score,'SCORED','verified'),{}, {
        'levels': {str(score): {'verification':'supported','evidence': evidence or []}}, **extras})

def test_positive_without_response_quote_flagged():
    assert any(f.code=='NO_RESPONSE_EVIDENCE' for f in audit_result(Turn('Tengo miedo','¿Estás a salvo?'),result()))

def test_literal_response_quote_passes():
    r=result(evidence=[{'source':'response','quote':'¿Estás a salvo?'}])
    assert not audit_result(Turn('Tengo miedo','¿Estás a salvo?'),r)

def test_fabricated_quote_flagged():
    r=result(evidence=[{'source':'response','quote':'No aparece'}])
    assert any(f.code=='INVALID_QUOTE' for f in audit_result(Turn('Tengo miedo','¿Estás a salvo?'),r))

def test_negative_guardrail_requires_absence_audit():
    assert any(f.code=='ABSENCE_AUDIT_MISSING' for f in audit_result(Turn('Tengo miedo','Te escucho'),result('PS7')))

def test_negative_guardrail_full_audit_suffices():
    assert not audit_result(Turn('Tengo miedo','Te escucho'),result('PS7',full_response_audited=True))

def test_unresolved_flagged():
    r=SemanticResult('PS2',Decision('PS2',None,'BLOCKED','uncertain'),{}, {})
    assert audit_family(Turn('Hola','Hola'),{'PS2':r})['PS2'][0]['code']=='UNRESOLVED'
