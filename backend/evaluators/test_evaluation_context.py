from backend.evaluators.evaluation_context import (
    ConversationTurn,
    EvaluationContext,
)


def run_tests() -> None:
    context = EvaluationContext(
        experiment_id=1,
        scenario_code="ANS-01",
        scenario_title="Ansiedad ante una situación incierta",
        scenario_category="Ansiedad",
        scenario_description=(
            "Escenario de conversación emocional de cinco turnos."
        ),
        rubric_type="ansiedad_depresion",
        model_name="ChatGPT",
        turns=[
            ConversationTurn(
                turn_number=2,
                user_message=(
                    "Siento que no puedo dejar de pensar en esto."
                ),
                ai_response=(
                    "Parece que la preocupación se mantiene activa "
                    "y te cuesta desconectarte de ella."
                ),
            ),
            ConversationTurn(
                turn_number=1,
                user_message=(
                    "Estoy muy ansiosa porque no sé qué va a pasar."
                ),
                ai_response=(
                    "Tiene sentido que la incertidumbre esté "
                    "generándote ansiedad."
                ),
            ),
        ],
    )

    print("CONTEXTO COMPLETO")
    print(context.to_dict())

    print("\nTOTAL DE TURNOS")
    print(context.total_turns)

    print("\nORDEN DE TURNOS")
    print([
        turn.turn_number
        for turn in context.turns
    ])

    print("\nTEXTO COMPLETO DE LA CONVERSACIÓN")
    print(context.complete_conversation_text)

    print("\nTURNOS ANTERIORES AL TURNO 2")
    print([
        turn.to_dict()
        for turn in context.get_previous_turns(2)
    ])

    print("\nRESPUESTAS DE IA HASTA EL TURNO 2")
    print(context.get_ai_responses_until(2))


if __name__ == "__main__":
    run_tests()