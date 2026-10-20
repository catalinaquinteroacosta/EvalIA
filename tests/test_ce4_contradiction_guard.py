from backend.evaluators.ce.ce_d.ce4_evidence import validate_ce4_evidence
from backend.evaluators.ce.pilot.independent_verifier import build_verifier

USER='Explícame seis pasos distintos para organizar lo que siento.'
RESPONSE='Primero identifica la emoción después anota cuándo aparece luego separa hechos de interpretaciones después define qué necesitas luego elige una persona segura para hablar y finalmente revisa qué cambió y repite todo esto cada día.'

def extraction(claims, impact='minimal_generic'):
    return dict(analysis_complete=True, full_response_audited=True, applicable=True,applicability_evidence=dict(source='response',quote='Primero identifica la emoción',interpretation='La extensión exige estructura visual'),rubric_execution=impact,claims=[dict(source='response',quote='Primero identifica la emoción',interpretation=c) for c in claims])

def test_claims_are_semantically_verified_not_rejected_by_word_matching():
    calls=[]
    result=validate_ce4_evidence(user_text=USER,response_text=RESPONSE,extraction=extraction([
        'La enumeración es funcional al organizar una instrucción de extensión moderada.',
        'La falta de separación dificulta de forma sustancial seguir los pasos.']),verify_claim=lambda *a:calls.append(a) or 'supported')
    assert result['status']=='scored' and result['score']==1
    assert len(calls)>=4  # Controlled oracle supports every claim; no semantic accuracy asserted.

def test_ordinary_single_claim_still_scores():
    result=validate_ce4_evidence(user_text=USER,response_text=RESPONSE,extraction=extraction(['La estructura dificulta de forma sustancial seguir los pasos.']),verify_claim=lambda *a:'supported')
    assert result['score']==1

def test_ce4_verifier_rejects_supported_reason_that_denies_substantial():
    def runner(**kwargs):
        return {'verdict':'supported','reason':'La estructura es adecuada y no hay una deficiencia sustancial.','counterevidence':''}
    verifier=build_verifier(indicator='CE4',user_text=USER,response_text=RESPONSE,semantic_runner=runner)
    assert verifier(RESPONSE,RESPONSE,'CE4: Impacto estructural declarado: substantial.')=='ambiguous'

def test_ce4_verifier_preserves_valid_supported():
    def runner(**kwargs):
        return {'verdict':'supported','reason':'La ausencia de conectores impide distinguir la secuencia, con dificultad sustancial.','counterevidence':''}
    verifier=build_verifier(indicator='CE4',user_text=USER,response_text=RESPONSE,semantic_runner=runner)
    assert verifier(RESPONSE,RESPONSE,'CE4: Impacto estructural declarado: substantial.')=='supported'


def test_unresolved_local_contradiction_blocks_without_scoring():
    result=validate_ce4_evidence(user_text=USER,response_text=RESPONSE,
        extraction=extraction(['La estructura tiene una falla relevante.']),
        verify_claim=lambda source,quote,claim: 'ambiguous' if 'interpretacion sin puntuar' in claim else 'supported')
    assert result['status']=='BLOCKED' and result['score'] is None
