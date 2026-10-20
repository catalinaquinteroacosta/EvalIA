from backend.evaluators.ps.contracts import Turn
from backend.evaluators.ps.runner import run_ps


def extract(system, payload):
    return {'indicator': payload['rubric']['code'], 'components': [], 'evidence': []}


def verifier(evidence, audit=False):
    def call(system, payload):
        code = payload['rubric']['code']
        return {'indicator': code, 'applicability': {'predicate':'applies','verification':'supported','evidence':[]},
                'levels': {str(i): {'verification':'supported' if i == 3 else 'unsupported',
                                   'evidence': evidence if i == 3 else []} for i in range(4)},
                'full_response_audited': audit}
    return call


def test_no_evidence_blocks_and_does_not_cache(tmp_path):
    t = Turn('Me preocupa esto', '¿Qué paso quieres intentar?')
    for _ in range(2):
        r = run_ps(t, extract_json=extract, verify_json=verifier([]),
                   extract_model='e', verify_model='v', cache_dir=tmp_path, codes=('PS1',))
        assert r.unresolved == ('PS1',)
        assert 'NO_RESPONSE_EVIDENCE' in r.results['PS1'].decision.reason
        assert any(e['stage']=='evidence_audit' for e in r.events)
        assert not any(e['source']=='cache_hit' for e in r.events)


def test_literal_evidence_allows_score_and_cache(tmp_path):
    t = Turn('Me preocupa esto', '¿Qué paso quieres intentar?')
    v = verifier([{'source':'response','quote':'¿Qué paso quieres intentar?'}])
    a = run_ps(t, extract_json=extract, verify_json=v, extract_model='e',
               verify_model='v', cache_dir=tmp_path, codes=('PS1',))
    assert a.results['PS1'].decision.score == 3
    b = run_ps(t, extract_json=extract, verify_json=v, extract_model='e',
               verify_model='v', cache_dir=tmp_path, codes=('PS1',))
    assert [x['source'] for x in b.events] == ['cache_hit','cache_hit']


def test_negative_guardrail_requires_full_response_audit(tmp_path):
    t = Turn('Me preocupa esto', 'Te escucho.')
    a = run_ps(t, extract_json=extract, verify_json=verifier([], False),
               extract_model='e', verify_model='v', cache_dir=tmp_path, codes=('PS7',))
    assert a.unresolved == ('PS7',)
    assert 'ABSENCE_AUDIT_MISSING' in a.results['PS7'].decision.reason


def test_negative_guardrail_audited_can_score(tmp_path):
    t = Turn('Me preocupa esto', 'Te escucho.')
    a = run_ps(t, extract_json=extract, verify_json=verifier([], True),
               extract_model='e', verify_model='v', cache_dir=tmp_path, codes=('PS7',))
    assert a.results['PS7'].decision.score == 3
