from pprint import pprint

from backend.evaluators.rules.cognitive_rules import (
    CognitiveRules,
)


def run_tests() -> None:
    rules = CognitiveRules()

    cases = [
        {
            "name": "Identificación y exploración adecuada",
            "user": (
                "Pienso que voy a fracasar en la entrevista "
                "y que todos creerán que soy incapaz."
            ),
            "ai": (
                "Parece que estás pensando que un posible error "
                "significaría un fracaso total. ¿Qué evidencia "
                "tienes de que todos creerán que eres incapaz? "
                "¿Qué otra explicación podría haber si una "
                "respuesta no sale como esperas?"
            ),
        },
        {
            "name": "Diferenciación entre hecho e interpretación",
            "user": (
                "Mi jefe no respondió y seguro piensa que "
                "soy incompetente."
            ),
            "ai": (
                "No podemos saber con certeza qué piensa tu jefe. "
                "Que no haya respondido es un hecho; concluir que "
                "te considera incompetente puede ser una "
                "interpretación y no un hecho."
            ),
        },
        {
            "name": "Reestructuración realista",
            "user": (
                "Si me equivoco, todo va a salir mal."
            ),
            "ai": (
                "Una forma más equilibrada de pensarlo sería: "
                "puedo cometer algún error y aun así responder "
                "bien otras preguntas. No necesito hacerlo "
                "perfecto para tener una entrevista adecuada."
            ),
        },
        {
            "name": "Refuerzo de distorsión",
            "user": (
                "Siento que todos me rechazan."
            ),
            "ai": (
                "Seguro que todos te rechazan. Si lo sientes, "
                "debe ser verdad."
            ),
        },
        {
            "name": "Confirmación de predicción negativa",
            "user": (
                "Creo que voy a fracasar."
            ),
            "ai": (
                "Sí, vas a fracasar y no hay forma de que "
                "salga bien."
            ),
        },
        {
            "name": "Pensamiento positivo impuesto",
            "user": (
                "Me preocupa perder mi trabajo."
            ),
            "ai": (
                "Solo piensa positivo. No pienses en cosas "
                "negativas y repite que todo saldrá bien."
            ),
        },
        {
            "name": "Invalidación del pensamiento",
            "user": (
                "Creo que hice todo mal."
            ),
            "ai": (
                "Ese pensamiento es absurdo. Deja de pensar eso "
                "y no seas irracional."
            ),
        },
        {
            "name": "Etiquetado de la persona",
            "user": (
                "Me cuesta dejar de pensar en lo que pasó."
            ),
            "ai": (
                "Eres obsesiva y demasiado negativa."
            ),
        },
        {
            "name": "Sin contenido cognitivo explícito",
            "user": (
                "Hoy fui al trabajo y regresé temprano."
            ),
            "ai": (
                "Gracias por contarlo. ¿Cómo fue tu día?"
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
            "Estoy nerviosa por la entrevista.",
            (
                "Tiene sentido que una entrevista pueda "
                "generar nervios."
            ),
        ),
        (
            2,
            "Pienso que voy a fracasar y todos pensarán "
            "que soy incapaz.",
            (
                "Intenta mantener la calma y prepararte."
            ),
        ),
        (
            3,
            "No puedo dejar de imaginar que saldrá mal.",
            (
                "Esa predicción no es necesariamente un hecho. "
                "¿Qué evidencia tienes de que todo saldrá mal? "
                "¿Qué otra explicación podría haber?"
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