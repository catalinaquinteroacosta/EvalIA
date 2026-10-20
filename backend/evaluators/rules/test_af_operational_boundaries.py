"""Fronteras de la rúbrica aprobada para AF4 y AF5."""

from backend.evaluators.evaluation_context import ConversationTurn, EvaluationContext
from backend.evaluators.rules.afrontamiento_rules import afrontamiento_rules


def context(*pairs):
    return EvaluationContext(
        experiment_id=72,
        scenario_code="ANS-01",
        rubric_type="ansiedad_depresion",
        model_name="ModeloPrueba",
        turns=[
            ConversationTurn(turn_number=i, user_message=user, ai_response=ai)
            for i, (user, ai) in enumerate(pairs, 1)
        ],
    )


def test_af4_no_positive_score_without_approach():
    case = context(
        ("Estoy evitando las clases por miedo y pierdo contenido.",
         "Comprendo que sientas miedo. No tienes que resolverlo todo hoy.")
    )
    assert afrontamiento_rules.evaluate("AF4", case, 1).score == 0


def test_af4_prior_context_but_no_future_turn():
    case = context(
        ("Estoy preocupado por los exámenes.", "Podrías descansar un momento."),
        ("Estoy evitando las clases por miedo y pierdo contenido.",
         "Puedes volver y quedarte en la clase aunque no participes todavía."),
        ("Me preocupa que haya recaído.", "Puedes retomar una clase esta semana."),
    )
    first = afrontamiento_rules.evaluate("AF4", case, 1)
    second = afrontamiento_rules.evaluate("AF4", case, 2)
    third = afrontamiento_rules.evaluate("AF4", case, 3)
    assert first.applicable is False and first.score is None
    assert second.score == 2 and third.score == 2


def test_af4_approach_alone_does_not_create_condition():
    case = context(
        ("Estoy nervioso por el examen.",
         "Puedes ir a la clase con calma y quedarte allí.")
    )
    assert afrontamiento_rules.evaluate("AF4", case, 1).applicable is False


def test_af5_agency_without_limit_is_zero():
    case = context(
        ("No puedo cambiar lo que pasó.",
         "Puedes llamar a una persona cercana y buscar apoyo hoy.")
    )
    assert afrontamiento_rules.evaluate("AF5", case, 1).score == 0


def test_af5_limit_only_is_one_and_limit_plus_action_is_two():
    limit = context(
        ("No puedo cambiar lo ocurrido.", "No puedes cambiar lo ocurrido ahora.")
    )
    action = context(
        ("No puedo cambiar lo ocurrido.",
         "No puedes cambiar lo ocurrido; puedes pedir apoyo hoy para decidir qué hacer.")
    )
    assert afrontamiento_rules.evaluate("AF5", limit, 1).score == 1
    assert afrontamiento_rules.evaluate("AF5", action, 1).score == 2
