
import socket
import pytest

from backend.evaluators.semantic import af_ai_af7 as af7


@pytest.mark.parametrize(
    "name, ai, action, quote, semantic_status, expected",
    [
        (
            "mencion_no_es_objetivo",
            "La preocupaci?n puede afectar tu sue?o. "
            "Si necesitas hablar, cu?ntaselo a alguien de confianza.",
            "dormir",
            "Si necesitas hablar",
            "not_supported",
            "not_supported",
        ),
        (
            "accion_retomada_explicita",
            "Antes de comenzar la primera pregunta, "
            "apoya los pies en el suelo y observa "
            "tres cosas a tu alrededor.",
            "comenzar las preguntas del examen",
            "Antes de comenzar la primera pregunta",
            "supported",
            "supported",
        ),
        (
            "referencia_contextual_valida",
            "Observa tres cosas a tu alrededor "
            "y despu?s intenta retomarlo.",
            "volver a estudiar",
            "despu?s intenta retomarlo",
            "supported",
            "supported",
        ),
    ],
)
def test_b_con_decisiones_semanticas_controladas(
    monkeypatch,
    name,
    ai,
    action,
    quote,
    semantic_status,
    expected,
):
    def forbid_network(*args, **kwargs):
        raise AssertionError("Intento de conexion externa")

    monkeypatch.setattr(
        socket.socket, "connect", forbid_network
    )
    monkeypatch.setattr(
        socket.socket, "connect_ex", forbid_network
    )

    calls = []

    def fake_entailment(**kwargs):
        calls.append(kwargs)
        return {
            "status": semantic_status,
            "reason": "Decision simulada de prueba",
        }

    monkeypatch.setattr(
        af7,
        "validate_semantic_entailment",
        fake_entailment,
    )

    result = af7._validate_b(
        item={
            "blocked_action": action,
            "blocked_action_user_id": "",
            "blocked_action_evidence": {
                "quote": quote,
                "source": "current_ai",
            },
        },
        interferences=[{
            "id": "interference_1",
            "action_description": action,
            "evidence": {
                "quote": "La ansiedad interfiere con " + action,
                "source": "current_user",
            },
        }],
        current_ai=ai,
        model="TEST",
        timeout=1,
    )

    assert calls, name
    assert result["status"] == expected, name

    if expected == "supported":
        assert (
            result["matched_interference_id"]
            == "interference_1"
        )
