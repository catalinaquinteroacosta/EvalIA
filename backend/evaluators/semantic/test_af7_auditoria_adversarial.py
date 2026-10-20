
import socket
import pytest
from backend.evaluators.semantic import af_ai_af7 as af7

@pytest.mark.parametrize("accion, respuesta, estado", [
    ("dormir",
     "La preocupaci?n afecta tu sue?o. Habla con alguien.",
     "not_supported"),
    ("comenzar el examen",
     "Antes de comenzar el examen, apoya los pies.",
     "supported"),
    ("volver a estudiar",
     "Observa tres cosas y despu?s intenta retomarlo.",
     "supported"),
])
def test_coherencia_adversarial(monkeypatch, accion, respuesta, estado):
    def prohibido(*args, **kwargs):
        raise AssertionError("Intento de conexion externa")

    monkeypatch.setattr(socket.socket, "connect", prohibido)
    monkeypatch.setattr(socket.socket, "connect_ex", prohibido)

    llamadas = []
    def validar(**kwargs):
        llamadas.append(kwargs)
        return {"status": estado, "reason": "Simulacion"}

    monkeypatch.setattr(af7, "validate_semantic_entailment", validar)

    resultado = af7._validate_joint_bt(
        item={
            "blocked_action": accion,
            "blocked_action_evidence": {
                "quote": respuesta, "source": "current_ai"
            },
            "procedure": "Procedimiento propuesto",
            "procedure_evidence": {
                "quote": respuesta, "source": "current_ai"
            },
        },
        b_validation={
            "status": "supported",
            "matched_interference_id": "interference_1",
        },
        interferences=[{
            "id": "interference_1",
            "action_description": accion,
            "evidence": {
                "quote": "Me cuesta " + accion,
                "source": "current_user",
            },
        }],
        current_ai=respuesta,
        model="TEST",
        timeout=1,
    )

    assert llamadas
    assert resultado["status"] == estado
    assert accion in llamadas[0]["proposition"]
    assert respuesta in llamadas[0]["evidence"]
