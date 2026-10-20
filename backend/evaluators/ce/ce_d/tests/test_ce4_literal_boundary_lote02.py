from backend.evaluators.ce.ce_d.ce4_evidence import validate_ce4_evidence


def test_ce4_invalid_literal_does_not_throw_or_score():
    response = 'Primero identifica lo ocurrido. Después registra lo que sentiste.'
    base = dict(analysis_complete=True, full_response_audited=True, applicable=True,
                rubric_execution='omitted_or_opposite', claims=[])
    for quote in ('', 'Cita inexistente'):
        extraction = dict(base, applicability_evidence=dict(
            source='response', quote=quote, interpretation='Extensión que requiere estructura'))
        calls = []
        def verifier(*args):
            calls.append(args)
            return 'supported'
        result = validate_ce4_evidence(user_text='Necesito orientación.',
            response_text=response, extraction=extraction, verify_claim=verifier)
        assert result == {'status': 'insufficient_evidence', 'score': None}
        assert not calls, 'No debe llamar OpenAI si la cita no es literal'


def test_ce4_literal_valid_but_claims_missing_is_not_scored():
    response = 'Primero identifica lo ocurrido. Después registra lo que sentiste.'
    extraction = dict(analysis_complete=True, full_response_audited=True, applicable=True,
        rubric_execution='omitted_or_opposite', claims=[], applicability_evidence=dict(
        source='response', quote='Primero identifica lo ocurrido.',
        interpretation='Extensión que requiere estructura'))
    result = validate_ce4_evidence(user_text='Necesito orientación.',
        response_text=response, extraction=extraction, verify_claim=lambda *args:'supported')
    assert result == {'status': 'insufficient_evidence', 'score': None}
