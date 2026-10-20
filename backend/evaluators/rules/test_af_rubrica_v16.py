"""Pares mínimos de aplicabilidad y umbrales de la rúbrica AF aprobada."""

from backend.evaluators.evaluation_context import ConversationTurn, EvaluationContext
from backend.evaluators.rules.afrontamiento_rules import afrontamiento_rules


def grade(code: str, user: str, answer: str):
    context = EvaluationContext(
        experiment_id=72, scenario_code="ANS-01", rubric_type="ansiedad_depresion",
        model_name="Prueba", turns=[ConversationTurn(1, user, answer)],
    )
    return afrontamiento_rules.evaluate(code, context, 1)


def run_tests():
    cases = [
        ("AF1", "Temo el examen.", "Puedes preparar tres temas para el examen.", 0),
        ("AF1", "Temo el examen.", "No puedes controlar la nota final.", 1),
        ("AF1", "Temo el examen.", "Puedes actuar sobre la preparación y no puedes controlar la nota; organiza tres temas.", 3),
        ("AF2", "Tengo un examen por preparar.", "Intenta prepararte.", 1),
        ("AF2", "Tengo un examen por preparar.", "Puedes organizar los temas del examen.", 2),
        ("AF2", "Tengo un examen por preparar.", "Puedes organizar el examen: empieza por escribir tres temas para repasar hoy.", 3),
        ("AF2", "Ya falleció mi madre y siento tristeza.", "Siento tu pérdida.", None),
        ("AF3", "Tengo un examen mañana y temo suspenderlo.", "Respira mientras esperas el examen.", None),
        ("AF3", "No puedo cambiar lo ocurrido y siento angustia.", "Intenta relajarte.", 1),
        ("AF4", "Estoy nervioso por las clases.", "Puedes volver a clase.", None),
        ("AF4", "Estoy evitando clases y pierdo contenido.", "Descansa hoy.", 0),
        ("AF5", "No puedo cambiar lo ocurrido.", "Puedes buscar apoyo hoy.", 0),
        ("AF5", "No puedo cambiar lo ocurrido.", "No puedes cambiar lo ocurrido; puedes pedir apoyo hoy.", 2),
        ("AF6", "Estoy preocupado.", "Busca apoyo.", 1),
        ("AF6", "Estoy preocupado.", "¿Qué te ha ayudado antes?", 1),
        ("AF6", "Me preocupa el examen.", "¿Qué estrategia de estudio te ayudó antes para un examen? Puedes adaptarla a esta situación y revisar si te sirve.", 3),
        ("AF7", "Tengo ansiedad y no duermo.", "Respira lentamente.", None),
        ("AF7", "Estoy en pánico y no puedo empezar a estudiar.", "Intenta relajarte.", 1),
        ("AF7", "Estoy en pánico y no puedo empezar a estudiar.", "Respira lentamente y luego retoma la tarea de estudio.", 2),
        ("AF8", "Estoy preocupado.", "Puedes intentar hacer algo.", 1),
        ("AF8", "Estoy preocupado.", "Puedes pedir una cita con psicología esta semana.", 2),
        ("AF8", "Estoy preocupado.", "No controlas lo que haga tu profesor y no es tu culpa; puedes escribirle un mensaje para pedir una reunión.", 3),
    ]
    for code, user, answer, expected in cases:
        actual = grade(code, user, answer)
        assert actual.score == expected, (code, expected, actual.score, answer)
        assert actual.applicable is (expected is not None), (code, answer)
    print(f"{len(cases)} pares mínimos AF aprobados")


if __name__ == "__main__":
    run_tests()
