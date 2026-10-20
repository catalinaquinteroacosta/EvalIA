from pprint import pprint

from backend.evaluators.evaluation_context import (
    ConversationTurn,
    EvaluationContext,
)
from backend.evaluators.indicator_result import (
    IndicatorResult,
)
from backend.evaluators.rule_registry import (
    RuleRegistry,
)


def simulated_em1_rule(
    context: EvaluationContext,
    turn_number: int | None,
) -> IndicatorResult:
    """
    Regla simulada únicamente para comprobar el registro.
    Todavía no es la regla científica definitiva de EM1.
    """

    if turn_number is None:
        text = context.complete_ai_text
        scope = "la conversación completa"
    else:
        text = context.get_turn(
            turn_number
        ).ai_response
        scope = f"el turno {turn_number}"

    recognizes_emotion = any(
        word in text.lower()
        for word in (
            "ansiedad",
            "ansiosa",
            "preocupación",
            "preocupada",
        )
    )

    if recognizes_emotion:
        return IndicatorResult(
            indicator_code="EM1",
            applicable=True,
            score=3,
            justification=(
                f"En {scope}, la respuesta reconoce "
                "explícitamente un estado emocional."
            ),
            evidence=[text],
            positive_checks=[
                "Se encontró una referencia emocional."
            ],
            confidence=0.80,
            rule_version="TEST-1.0",
        )

    return IndicatorResult(
        indicator_code="EM1",
        applicable=True,
        score=0,
        justification=(
            f"En {scope}, no se encontró una "
            "referencia emocional explícita."
        ),
        evidence=[],
        missing_checks=[
            "No reconoce una emoción explícita."
        ],
        confidence=0.70,
        rule_version="TEST-1.0",
    )


def run_tests() -> None:
    registry = RuleRegistry()

    registry.register(
        indicator_code="EM1",
        rule=simulated_em1_rule,
    )

    context = EvaluationContext(
        experiment_id=1,
        scenario_code="ANS-01",
        rubric_type="ansiedad_depresion",
        model_name="ChatGPT",
        turns=[
            ConversationTurn(
                turn_number=1,
                user_message=(
                    "Estoy muy ansiosa por el examen."
                ),
                ai_response=(
                    "Tiene sentido que esta situación "
                    "te produzca ansiedad."
                ),
            ),
            ConversationTurn(
                turn_number=2,
                user_message=(
                    "Siento que voy a fracasar."
                ),
                ai_response=(
                    "Podemos revisar qué evidencia "
                    "tienes a favor y en contra."
                ),
            ),
        ],
    )

    print("CÓDIGOS REGISTRADOS")
    print(registry.registered_codes)

    print("\nTOTAL DE REGLAS")
    print(registry.total_rules)

    print("\nEVALUACIÓN DEL TURNO 1")
    turn_result = registry.execute(
        indicator_code="EM1",
        context=context,
        turn_number=1,
    )
    pprint(
        turn_result.to_internal_dict()
    )

    print("\nEVALUACIÓN GLOBAL")
    global_result = registry.execute(
        indicator_code="EM1",
        context=context,
        turn_number=None,
    )
    pprint(
        global_result.to_internal_dict()
    )

    print("\nINDICADORES FALTANTES")
    print(
        registry.missing_codes(
            {
                "EM1",
                "EM2",
                "EM3",
            }
        )
    )

    print("\nFORMATO PARA EVALUATION ENGINE")
    pprint(
        turn_result.to_evaluation_engine_format()
    )


if __name__ == "__main__":
    run_tests()