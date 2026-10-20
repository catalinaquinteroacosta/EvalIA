from backend.evaluators.ansiedad_semantic.functional_review import definitions


def test_pa1_requires_identified_action_without_inference():
    text = definitions('PA1')['observable_problem_related_action']
    assert 'no especifica una acción observable' in text
    assert 'No completar la acción por inferencia' in text


def test_ir2_requires_contextual_referents_in_both_components():
    for name in ('observable_fact_distinguished', 'interpretation_distinguished'):
        text = definitions('IR2')[name]
        assert 'hecho concreto y la interpretación concreta' in text
        assert 'No inventar los referentes' in text
