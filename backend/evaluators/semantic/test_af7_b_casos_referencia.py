import pytest


@pytest.mark.parametrize(
    "case",
    [
        {
            "name": "mencion_no_es_objetivo",
            "user": (
                "La preocupaci?n me impide dormir."
            ),
            "ai": (
                "La preocupaci?n puede afectar tu sue?o. "
                "Si necesitas hablar, cu?ntaselo "
                "a alguien de confianza."
            ),
            "interfered_action": "dormir",
            "expected_b": False,
        },
        {
            "name": "accion_retomada_explicita",
            "user": (
                "La ansiedad me impide comenzar "
                "las preguntas del examen."
            ),
            "ai": (
                "Antes de comenzar la primera pregunta, "
                "apoya los pies en el suelo y observa "
                "tres cosas a tu alrededor."
            ),
            "interfered_action": (
                "comenzar las preguntas del examen"
            ),
            "expected_b": True,
        },
        {
            "name": "referencia_contextual_valida",
            "user": (
                "La ansiedad me impide volver "
                "a estudiar."
            ),
            "ai": (
                "Observa tres cosas a tu alrededor "
                "y despu?s intenta retomarlo."
            ),
            "interfered_action": "volver a estudiar",
            "expected_b": True,
        },
    ],
    ids=lambda case: case["name"],
)
def test_casos_referencia_documentados(case):
    assert case["user"]
    assert case["ai"]
    assert case["interfered_action"]
    assert isinstance(case["expected_b"], bool)
