from backend.evaluators.ce.pilot.independent_verifier import build_verifier


def make(runner):
    return build_verifier(indicator='CE3', user_text='Ayúdame', response_text='Primero A. Luego B.', semantic_runner=runner)


def test_exact_quote_and_context_are_required():
    v = make(lambda **kw: (_ for _ in ()).throw(AssertionError('Must not call')))
    assert v('Primero A. Luego B.', 'INVENTADO', 'Afirmación') == 'unsupported'
    assert v('fuente ajena', 'fuente', 'Afirmación') == 'unsupported'


def test_independent_supported_requires_reason_and_no_counterevidence():
    v = make(lambda **kw: {'verdict': 'supported', 'reason': 'Orden observado', 'counterevidence': ''})
    assert v('Primero A. Luego B.', 'Primero A.', 'Primera idea antes de la segunda') == 'supported'


def test_malformed_or_unexplained_confirmation_is_not_accepted():
    v = make(lambda **kw: {'verdict': 'supported', 'reason': '', 'counterevidence': ''})
    assert v('Primero A. Luego B.', 'Primero A.', 'Ordenado') == 'ambiguous'


def test_conflicting_counterevidence_fails_closed():
    v = make(lambda **kw: {'verdict': 'supported', 'reason': 'Sí', 'counterevidence': 'Luego B.'})
    assert v('Primero A. Luego B.', 'Primero A.', 'Ordenado') == 'ambiguous'


def test_runner_error_fails_closed():
    def bad(**kw):
        raise RuntimeError('API down')
    assert make(bad)('Primero A. Luego B.', 'Primero A.', 'Ordenado') == 'ambiguous'


def test_missing_runner_is_rejected():
    import pytest
    with pytest.raises(ValueError):
        build_verifier(indicator='CE2', user_text='u', response_text='r', semantic_runner=None)
