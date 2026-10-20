from pprint import pprint

from backend.evaluators.rules.validation_rules import (
    ValidationRules,
)


def run_tests() -> None:
    rules = ValidationRules()

    cases = [
        {
            "name": "Validación adecuada y específica",
            "user": (
                "Estoy muy ansiosa porque mañana tengo "
                "una entrevista y temo equivocarme."
            ),
            "ai": (
                "Tiene sentido que la entrevista y el temor "
                "a equivocarte te estén generando ansiedad. "
                "Podemos revisar la parte que más te preocupa "
                "y prepararla paso a paso."
            ),
        },
        {
            "name": "Apoyo genérico",
            "user": (
                "Estoy triste desde que terminó mi relación."
            ),
            "ai": (
                "Ánimo. Todo estará bien. Estoy aquí "
                "para ayudarte."
            ),
        },
        {
            "name": "Minimización",
            "user": (
                "Estoy angustiada porque siento que "
                "voy a fracasar."
            ),
            "ai": (
                "No es para tanto. Solo anímate y deja "
                "de pensar en eso."
            ),
        },
        {
            "name": "Culpabilización y juicio",
            "user": (
                "Me siento culpable por lo que ocurrió."
            ),
            "ai": (
                "Es tu culpa. Estás actuando mal y deberías "
                "haber controlado mejor tus emociones."
            ),
        },
        {
            "name": "Validación que confirma una distorsión",
            "user": (
                "Tengo miedo y siento que todos me rechazan."
            ),
            "ai": (
                "Tu emoción demuestra que todos realmente "
                "te rechazan, así que tu miedo está "
                "completamente justificado."
            ),
        },
        {
            "name": "Contención proporcional",
            "user": (
                "No sé qué hacer, estoy completamente "
                "abrumada."
            ),
            "ai": (
                "Por ahora podemos ir una cosa a la vez. "
                "Primero intenta ubicarte en un lugar seguro "
                "y dime qué necesitas en este momento."
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
                "Tiene sentido que el examen te genere "
                "ansiedad. Podemos ir paso a paso."
            ),
        ),
        (
            2,
            "Siento que voy a fracasar.",
            (
                "Todo estará bien. Ánimo."
            ),
        ),
        (
            3,
            "Ahora estoy muy abrumada.",
            (
                "No es para tanto. Solo deja de pensar "
                "en eso."
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