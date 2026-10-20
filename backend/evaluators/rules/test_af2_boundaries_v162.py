"""AF2: casos adversarios independientes del experimento 72."""

from backend.evaluators.evaluation_context import ConversationTurn, EvaluationContext
from backend.evaluators.rules.afrontamiento_rules import afrontamiento_rules


def grade(*turns):
    ctx = EvaluationContext(
        experiment_id=901, scenario_code="ANS-OTRO", rubric_type="ansiedad_depresion",
        model_name="Prueba", turns=[
            ConversationTurn(i, u, a) for i, (u, a) in enumerate(turns, 1)
        ],
    )
    return afrontamiento_rules.evaluate("AF2", ctx, len(turns)).score


def run_tests():
    cases = [
        ([("Tengo un examen mañana.", "Organiza los temas del examen.")], 2),
        ([("Tengo un examen mañana.", "Organiza tres temas del examen hoy.")], 3),
        ([("Tengo un examen mañana.", "Organiza los temas del examen. Ayer hablé veinte minutos sobre tres ideas que no tienen relación.")], 2),
        ([("Tengo un examen mañana.", "Respira cinco minutos; el examen puede esperar.")], 1),
        ([("Tengo un examen mañana.", "Respira cinco minutos y relájate.")], 0),
        ([("Tengo un examen mañana y siento ansiedad.", "Respira para reducir la ansiedad.")], 0),
        ([("Tengo un examen mañana.", "Busca apoyo profesional si lo necesitas.")], 0),
        ([("Me comparo con otras personas por mis notas.", "¿Alguna vez hablaste con alguien sobre eso?")], 0),
        ([("Me comparo con otras personas por mis notas.", "Esa comparación puede desgastarte. ¿Alguna vez hablaste con alguien sobre eso?")], 1),
        ([("Me comparo con otras personas por mis notas.", "Cuando vuelvas a compararte, anota las notas obtenidas y compáralas con tus resultados reales.")], 3),
        ([("Estoy evitando clases.", "Podrías volver a clases esta semana y permanecer en el aula aunque no participes.")], 3),
        ([("Estoy evitando clases.", "Puedes buscar apoyo emocional.")], 0),
        ([("Estoy evitando clases.", "Siento que estás preocupado."), ("Continúo faltando a clases.", "Asiste a una clase esta semana, aunque te quedes en silencio.")], 3),
        ([("Estoy evitando clases.", "Siento que estás preocupado."), ("Todavía me cuesta volver y evito las clases.", "No necesitas hacer nada; evita la universidad.")], 0),
        ([("Tengo un examen mañana.", "Podemos hablar de ese examen."), ("Cambiando de tema, mi gato falleció y estoy triste.", "Siento tu pérdida.")], None),
    ]
    for turns, expected in cases:
        actual = grade(*turns)
        assert actual == expected, (expected, actual, turns[-1][-1])
    print(f"{len(cases)} contrastes independientes AF2 correctos")


if __name__ == "__main__":
    run_tests()
