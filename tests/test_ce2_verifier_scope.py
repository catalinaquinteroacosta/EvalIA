from backend.evaluators.ce.pilot.independent_verifier import build_verifier


def test_ce2_verifier_separates_omission_from_overload():
    seen = []
    def runner(**kw):
        seen.append(kw['prompt'])
        return {'verdict':'supported', 'reason':'Respuesta íntegra breve, sin sobrecarga', 'counterevidence':''}
    v = build_verifier(indicator='CE2', user_text='Dame dos acciones para preparar la conversación.', response_text='De acuerdo.', semantic_runner=runner)
    assert v('De acuerdo.', 'De acuerdo.', "CE2, campo overload, VALOR DECLARADO: 'none'. No hay exceso de información") == 'supported'
    assert 'Una respuesta vacía o' in seen[0]
    assert 'overload=none simultáneamente' in seen[0]


def test_ce2_verifier_still_fails_closed_on_genuine_uncertainty():
    def runner(**kw):
        return {'verdict':'ambiguous','reason':'Hay duda genuina sobre contenido irrelevante','counterevidence':''}
    v = build_verifier(indicator='CE2', user_text='Necesito pasos', response_text='Mucho texto', semantic_runner=runner)
    assert v('Mucho texto','Mucho texto', 'overload=none') == 'ambiguous'


def test_other_indicators_do_not_receive_ce2_scope():
    seen=[]
    def runner(**kw):
        seen.append(kw['prompt']); return {'verdict':'supported','reason':'Verificado','counterevidence':''}
    v=build_verifier(indicator='CE3',user_text='u',response_text='r',semantic_runner=runner)
    assert v('r','r','orden') == 'supported'
    assert 'ALCANCE ESTRICTO CE2' not in seen[0]
