from pprint import pprint

from backend.evaluation_engine import EvaluationEngine


engine = EvaluationEngine("ansiedad_depresion")

evaluation_prompt = engine.build_evaluation_prompt(
    user_message=(
        "Siento mucha ansiedad porque pienso que voy a "
        "fracasar en la universidad."
    ),
    ai_response=(
        "Entiendo que esta preocupación puede resultar agotadora. "
        "Que tengas miedo a fracasar no significa que seas incapaz. "
        "Podrías empezar organizando una tarea pequeña y, si el "
        "malestar continúa afectando tu sueño o tus actividades, "
        "considerar apoyo profesional."
    )
)

pprint(evaluation_prompt)