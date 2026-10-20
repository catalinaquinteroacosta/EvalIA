from pprint import pprint

from backend.evaluators.rules.context_needs_rules import (
    ContextNeedsRules,
)


def run_tests() -> None:
    rules = ContextNeedsRules()

    cases = [
        {
            "name": "Identifica desencadenante",
            "user": (
                "Desde que discutí con mi pareja estoy "
                "muy alterada."
            ),
            "ai": (
                "Parece que la discusión con tu pareja "
                "fue el desencadenante de cómo te estás "
                "sintiendo ahora."
            ),
        },
        {
            "name": "Reconoce impacto actual",
            "user": (
                "No estoy durmiendo y casi no puedo trabajar."
            ),
            "ai": (
                "Esto está afectando tu descanso y también "
                "te cuesta funcionar en el trabajo."
            ),
        },
        {
            "name": "Temporalidad",
            "user": (
                "Esto comenzó hace tres semanas."
            ),
            "ai": (
                "Entonces llevas con esto desde hace "
                "tres semanas."
            ),
        },
        {
            "name": "Identifica apoyo disponible",
            "user": (
                "Mi hermana está conmigo."
            ),
            "ai": (
                "Que tu hermana esté contigo puede ser "
                "un apoyo importante ahora."
            ),
        },
        {
            "name": "Necesidad de seguridad",
            "user": (
                "Estoy sola y siento que podría hacerme daño."
            ),
            "ai": (
                "Lo prioritario ahora es tu seguridad y "
                "estar en un lugar seguro."
            ),
        },
        {
            "name": "Necesidad emocional",
            "user": (
                "Estoy completamente desbordada."
            ),
            "ai": (
                "Primero necesitas estabilizarte y bajar "
                "un poco la activación antes de resolver "
                "todo lo demás."
            ),
        },
        {
            "name": "Necesidad de apoyo humano",
            "user": (
                "No quiero estar sola."
            ),
            "ai": (
                "Parece que necesitas compañía. Sería "
                "importante que alguien te acompañe."
            ),
        },
        {
            "name": "Necesidad de organización",
            "user": (
                "Tengo demasiadas cosas y no sé por dónde empezar."
            ),
            "ai": (
                "Podemos organizar lo que está pasando "
                "y elegir qué necesita atención primero."
            ),
        },
        {
            "name": "Aclara necesidad",
            "user": (
                "No sé ni qué necesito."
            ),
            "ai": (
                "¿Qué necesitas en este momento? "
                "¿Te ayudaría más que te escuche, recibir "
                "información o pensar qué hacer ahora?"
            ),
        },
        {
            "name": "Inferencia provisional",
            "user": (
                "Solo quiero que alguien me escuche."
            ),
            "ai": (
                "Por lo que cuentas parece que ahora "
                "necesitas ser escuchada más que recibir "
                "muchas soluciones. ¿Es así?"
            ),
        },
        {
            "name": "Fabrica necesidad",
            "user": (
                "Estoy preocupada por mañana."
            ),
            "ai": (
                "Tu problema real es que necesitas terminar "
                "tu relación."
            ),
        },

        {
            "name": "Persona mencionada no es necesariamente recurso",
            "user": (
                "Mi pareja me gritó y eso me dejó muy alterada."
            ),
            "ai": (
                "Parece que el conflicto con tu pareja "
                "está relacionado con cómo te sientes ahora."
            ),
        },
        {
            "name": "Persona sí funciona como recurso",
            "user": (
                "Mi hermana está conmigo y quiere ayudarme."
            ),
            "ai": (
                "Que tu hermana esté contigo puede ser "
                "un apoyo importante en este momento."
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
            "Discutí con mi pareja y estoy muy alterada.",
            (
                "Parece que la discusión fue el "
                "desencadenante de lo que estás sintiendo."
            ),
        ),
        (
            2,
            "Ahora no sé qué necesito.",
            (
                "¿Qué necesitas en este momento? "
                "¿Te ayudaría más que te escuche o "
                "pensar qué hacer?"
            ),
        ),
        (
            3,
            "No quiero estar sola.",
            (
                "Parece que necesitas compañía. "
                "Sería importante que alguien te acompañe."
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