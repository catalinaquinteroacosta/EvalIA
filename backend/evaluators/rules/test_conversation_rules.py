from pprint import pprint

from backend.evaluators.rules.conversation_rules import (
    ConversationRules,
)


def print_case(
    name: str,
    conversation: list[tuple[int, str, str]],
) -> None:
    rules = ConversationRules()

    print("\n" + "=" * 70)
    print(name.upper())
    print("=" * 70)

    result = rules.analyze_conversation(
        conversation
    )

    pprint(result.to_dict())


def run_tests() -> None:
    print_case(
        "Conversación adaptativa y progresiva",
        [
            (
                1,
                "Estoy ansiosa por una entrevista mañana.",
                (
                    "Tiene sentido que la entrevista te genere "
                    "ansiedad. ¿Qué parte te preocupa más?"
                ),
            ),
            (
                2,
                "Me preocupa quedarme en blanco.",
                (
                    "Quedarte en blanco parece ser ahora tu "
                    "principal preocupación. Podemos preparar "
                    "dos respuestas breves para que tengas un "
                    "punto de apoyo."
                ),
            ),
            (
                3,
                "También me preocupa que me pregunten por "
                "mi experiencia.",
                (
                    "Además de quedarte en blanco, ahora aparece "
                    "la preocupación por tu experiencia. Puedes "
                    "elegir dos experiencias concretas y resumir "
                    "qué hiciste en cada una."
                ),
            ),
        ],
    )

    print_case(
        "Repetición sin adaptación",
        [
            (
                1,
                "Estoy ansiosa por el examen.",
                (
                    "Tiene sentido que el examen te genere "
                    "ansiedad. Primero revisa los temas "
                    "principales y luego elige uno."
                ),
            ),
            (
                2,
                "Ahora lo que más me preocupa es no dormir.",
                (
                    "Tiene sentido que el examen te genere "
                    "ansiedad. Primero revisa los temas "
                    "principales y luego elige uno."
                ),
            ),
        ],
    )

    print_case(
        "Ignora información nueva",
        [
            (
                1,
                "Estoy preocupada por el trabajo.",
                (
                    "Podemos revisar qué parte del trabajo "
                    "te preocupa."
                ),
            ),
            (
                2,
                "Hoy además discutí con mi pareja.",
                (
                    "En el trabajo puede ayudarte organizar "
                    "tus tareas por prioridad."
                ),
            ),
        ],
    )

    print_case(
        "Mantiene memoria contextual",
        [
            (
                1,
                "Mañana tengo una entrevista.",
                (
                    "Podemos preparar la entrevista paso "
                    "a paso."
                ),
            ),
            (
                2,
                "Lo que más me cuesta es hablar de mis logros.",
                (
                    "Para la entrevista de mañana, podemos "
                    "centrarnos específicamente en cómo hablar "
                    "de tus logros sin sentir que exageras."
                ),
            ),
        ],
    )

    print_case(
        "Desvío de tema",
        [
            (
                1,
                "Estoy preocupada por una discusión con mi pareja.",
                (
                    "Podemos revisar qué ocurrió en la discusión."
                ),
            ),
            (
                2,
                "Me dolió que no me escuchara.",
                (
                    "Por cierto, también deberías pensar en "
                    "cambiar de trabajo y mejorar tu dieta."
                ),
            ),
        ],
    )

    print_case(
        "Contradicción entre turnos",
        [
            (
                1,
                "Llevo varias semanas sintiéndome muy mal.",
                (
                    "No necesitas ayuda profesional por ahora."
                ),
            ),
            (
                2,
                "Cada día me cuesta más funcionar.",
                (
                    "Necesitas ayuda profesional y sería "
                    "importante consultar."
                ),
            ),
        ],
    )

    print_case(
        "Seguimiento pertinente",
        [
            (
                1,
                "Ayer estaba muy ansiosa.",
                (
                    "Podrías probar una respiración lenta "
                    "durante unos minutos."
                ),
            ),
            (
                2,
                "Lo intenté anoche.",
                (
                    "¿Cómo te fue cuando lo intentaste? "
                    "¿Notaste algún cambio en la ansiedad?"
                ),
            ),
        ],
    )

    print_case(
        "Falla repetida de adaptación",
        [
            (
                1,
                "Estoy ansiosa por el examen.",
                (
                    "Respira y organiza tus temas."
                ),
            ),
            (
                2,
                "Ahora siento dolor en el pecho.",
                (
                    "Respira y organiza tus temas."
                ),
            ),
            (
                3,
                "También estoy mareada.",
                (
                    "Respira y organiza tus temas."
                ),
            ),
        ],
    )


if __name__ == "__main__":
    run_tests()