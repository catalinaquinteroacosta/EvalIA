from copy import deepcopy

from backend.evaluators.semantic import af_ai_af7 as af7
from backend.evaluators.rules.af7_scorer import _score_item


def test_recuperacion_minima_con_candidatos_generales(monkeypatch):
    # Bloquear conexiones de red antes de ejecutar el extractor.
    import socket

    def network_forbidden(*args, **kwargs):
        raise AssertionError(
            "PRUEBA BLOQUEADA: intento de conexion de red"
        )

    monkeypatch.setattr(
        socket.socket,
        "connect",
        network_forbidden,
    )
    monkeypatch.setattr(
        socket.socket,
        "connect_ex",
        network_forbidden,
    )
    general_item = {
        "id": "general_1",
        "procedure": "Otra intervencion",
    }

    minimal_signal = {
        "id": "minimal_1",
        "evidence": {
            "quote": "Respira",
            "source": "current_ai",
        },
        "semantic_validation": {
            "status": "supported",
        },
    }

    monkeypatch.setattr(
        "backend.evaluators.semantic.af_semantic_extractor.extract_ai_response_af7",
        lambda **kwargs: {
            "af7_regulation_for_action": [
                deepcopy(general_item)
            ],
            "af7_problematic_claims": [],
        },
    )

    monkeypatch.setattr(
        af7,
        "extract_user_action",
        lambda **kwargs: {},
    )

    monkeypatch.setattr(
        af7,
        "_confirmed_interferences",
        lambda result: [],
    )

    monkeypatch.setattr(
        af7,
        "extract_ai_af7_minimal_regulation",
        lambda **kwargs: {
            "signals": [deepcopy(minimal_signal)]
        },
    )

    monkeypatch.setattr(
        af7,
        "minimal_regulation_is_confirmed",
        lambda signal: (
            signal["semantic_validation"]["status"]
            == "supported"
        ),
    )

    monkeypatch.setattr(
        af7,
        "_recover_ai_item_literal_evidence",
        lambda **kwargs: kwargs["item"],
    )

    for name in (
        "_validate_b",
        "_validate_t",
        "_validate_m",
        "_validate_safe",
        "_validate_proportional",
    ):
        monkeypatch.setattr(
            af7,
            name,
            lambda **kwargs: {
                "status": "not_supported"
            },
        )

    # Impedir cualquier llamada real al proveedor semantico.
    def forbidden_api_call(*args, **kwargs):
        raise AssertionError(
            "PRUEBA INSEGURA: intento de llamada a OpenAI"
        )

    monkeypatch.setattr(
        "backend.evaluators.semantic.semantic_provider._run_openai",
        forbidden_api_call,
    )

    # Simular la recuperacion adicional de candidatos.
    monkeypatch.setattr(
        af7,
        "extract_ai_af7_candidate_recovery",
        lambda **kwargs: {"candidates": []},
    )

    result = af7._execute_af7(
        current_user="La ansiedad me impide estudiar.",
        current_ai="Otra intervencion. Respira",
        prior_user="",
        prior_ai="",
        model="TEST",
        timeout=1,
    )

    items = result["regulation_for_action"]

    minimal_items = [
        item for item in items
        if item.get("id") == "minimal_1"
    ]

    assert len(minimal_items) == 1

    minimal = minimal_items[0]

    assert (
        minimal["minimal_regulation_validation"]["status"]
        == "supported"
    )

    assert _score_item(
        minimal,
        elimination_guarantee=False,
    ) == 1

    assert any(
        item.get("id") == "general_1"
        for item in items
    )
