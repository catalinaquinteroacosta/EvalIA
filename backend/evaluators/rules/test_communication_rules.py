from pprint import pprint

from backend.evaluators.rules.communication_rules import (
    CommunicationRules,
)


def run_tests() -> None:
    rules = CommunicationRules()

    cases = [
        {
            "name": "Respuesta clara, estructurada y enfocada",
            "user": (
                "Estoy ansiosa por la entrevista de mañana "
                "y no sé cómo prepararme."
            ),
            "ai": (
                "Tiene sentido que la entrevista te genere ansiedad. "
                "Primero identifica las tres preguntas que más te "
                "preocupan. Después practica respuestas breves y, "
                "por último, prepara una pregunta para el entrevistador. "
                "¿Qué parte de la entrevista te preocupa más?"
            ),
        },
        {
            "name": "Respuesta demasiado breve",
            "user": (
                "Estoy triste porque terminó mi relación."
            ),
            "ai": (
                "Ánimo. Todo estará bien."
            ),
        },
        {
            "name": "Respuesta genérica",
            "user": (
                "Estoy ansiosa por perder mi empleo."
            ),
            "ai": (
                "No te preocupes. Piensa positivo y sé fuerte."
            ),
        },
        {
            "name": "Lenguaje técnico sin explicación",
            "user": (
                "Siento que me desconecto de la realidad."
            ),
            "ai": (
                "Eso puede corresponder a desrealización, "
                "despersonalización y sintomatología disociativa."
            ),
        },
        {
            "name": "Lenguaje técnico explicado",
            "user": (
                "Siento que me desconecto de la realidad."
            ),
            "ai": (
                "A veces se usa el término desrealización; "
                "es decir, una sensación de que el entorno "
                "se percibe extraño o poco real."
            ),
        },
        {
            "name": "Respuesta fragmentada",
            "user": (
                "Estoy abrumada y necesito organizarme."
            ),
            "ai": (
                "Respira. Pausa. Escribe. Revisa. Decide."
            ),
        },
        {
            "name": "Desvío de foco",
            "user": (
                "Estoy preocupada por una discusión con mi pareja."
            ),
            "ai": (
                "Podrías hablar con tu pareja. Por cierto, "
                "también deberías revisar tus hábitos de sueño "
                "y pensar en cambiar de trabajo."
            ),
        },
    ]

    for case in cases:
        print("\n" + "=" * 70)
        print(case["name"].upper())
        print("=" * 70)

        result = rules.analyze(
            user_message=case["user"],
            ai_response=case["ai"],
        )

        pprint(result.to_dict())

    conversation = [
        (
            1,
            "Estoy ansiosa por el examen.",
            (
                "Tiene sentido que el examen te genere ansiedad. "
                "Primero revisa los temas principales y después "
                "elige uno para comenzar."
            ),
        ),
        (
            2,
            "Me preocupa no recordar nada.",
            (
                "Tiene sentido que el examen te genere ansiedad. "
                "Primero revisa los temas principales y después "
                "elige uno para comenzar."
            ),
        ),
        (
            3,
            "¿Qué puedo hacer hoy?",
            (
                "Puedes empezar por estudiar durante veinte "
                "minutos y luego revisar qué tanto recuerdas."
            ),
        ),
    ]

    print("\n" + "=" * 70)
    print("ANÁLISIS DE CONVERSACIÓN")
    print("=" * 70)

    pprint(
        rules.analyze_conversation(
            conversation
        )
    )


if __name__ == "__main__":
    run_tests()