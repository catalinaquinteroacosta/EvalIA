"""Offline adversarial contract tests; NOT a substitute for live rubric validation."""
import pytest
from backend.evaluators.ps.contracts import Turn, HistoryMessage, Evidence, Claim
from backend.evaluators.ps.evidence import verify_literal, EvidenceError
from backend.evaluators.ps.scoring import decide, CODES, CONDITIONAL
from backend.evaluators.ps.rubric import rubric_for
from backend.evaluators.ps.cache import key_for
from backend.evaluators.ps.semantic import evaluate_one, SemanticProtocolError


def claim(code, predicate, verification='supported', evidence=()):
    return Claim(code, predicate, tuple(evidence), verification)


def levels(code, winning=3):
    return {i: claim(code, f'level_{i}_matches', 'supported' if i == winning else 'unsupported') for i in range(4)}


@pytest.mark.parametrize('code', CODES)
def test_all_ten_have_official_four_levels(code):
    rubric = rubric_for(code)
    assert rubric['code'] == code
    assert rubric['question'].strip()
    assert len(rubric['reference_levels']) == 4
    assert all(str(i) in rubric['reference_levels'] or i in rubric['reference_levels'] for i in range(4))


@pytest.mark.parametrize('code', CODES)
def test_all_ten_reject_conflicting_level_matches(code):
    t = Turn('Necesito ayuda', 'Estoy aquí para ayudarte')
    ls = levels(code)
    ls[2] = claim(code, 'level_2_matches', 'supported')
    assert decide(t, code, claim(code, 'applies'), ls).status == 'BLOCKED'


@pytest.mark.parametrize('code', CODES)
def test_all_ten_reject_ambiguous_level_matches(code):
    t = Turn('Necesito ayuda', 'Estoy aquí para ayudarte')
    ls = levels(code)
    ls[3] = claim(code, 'level_3_matches', 'ambiguous')
    assert decide(t, code, claim(code, 'applies'), ls).status == 'BLOCKED'


@pytest.mark.parametrize('code', CODES)
def test_na_only_for_conditional_indicators(code):
    t = Turn('Hola', 'Hola')
    result = decide(t, code, claim(code, 'not_applicable'), {})
    assert result.status == ('NA' if code in CONDITIONAL else 'BLOCKED')


def test_quote_cannot_be_taken_from_other_history_message():
    t = Turn('ahora', 'respuesta', (HistoryMessage('user', 'primero'), HistoryMessage('assistant', 'segundo')))
    with pytest.raises(EvidenceError):
        verify_literal(t, Evidence('history', 'primero', 1))


def test_quote_must_be_exact_case_sensitive():
    with pytest.raises(EvidenceError):
        verify_literal(Turn('Estoy Triste', 'Respuesta'), Evidence('user', 'estoy triste'))


def test_no_history_index_for_current_response():
    with pytest.raises(EvidenceError):
        verify_literal(Turn('Hola', 'Respuesta'), Evidence('response', 'Respuesta', 0))


def test_verified_claim_with_fabricated_quote_blocks():
    code = 'PS10'
    ls = levels(code)
    ls[3] = claim(code, 'level_3_matches', evidence=(Evidence('response', 'cita inventada'),))
    result = decide(Turn('Problema', 'Respuesta'), code, claim(code, 'applies'), ls)
    assert result.status == 'BLOCKED'


def test_model_prompt_change_invalidates_cache_key():
    r = rubric_for('PS9')
    payload = {'turn': {'user': 'u', 'response': 'r', 'prior_history': []}, 'rubric': r}
    a = key_for('verify', code='PS9', model='m', system='prompt A', payload=payload, rubric=r)
    b = key_for('verify', code='PS9', model='m', system='prompt B', payload=payload, rubric=r)
    assert a != b


def test_model_change_invalidates_cache_key():
    r = rubric_for('PS9')
    payload = {'turn': {'user': 'u', 'response': 'r', 'prior_history': []}, 'rubric': r}
    a = key_for('verify', code='PS9', model='m1', system='p', payload=payload, rubric=r)
    b = key_for('verify', code='PS9', model='m2', system='p', payload=payload, rubric=r)
    assert a != b


def test_extractor_must_not_assign_score():
    def extractor(system, payload):
        return {'indicator': 'PS1', 'score': 3, 'components': [], 'evidence': []}
    def verifier(*args):
        raise AssertionError('Verifier should not be called')
    with pytest.raises(SemanticProtocolError):
        evaluate_one(Turn('Problema', 'Respuesta'), 'PS1', extractor, verifier)
