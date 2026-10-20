from unittest.mock import patch

import pytest

from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.nd.semantic_engine import (
    NDSemanticEngine,
)


def make_engine(tmp_path):
    # Mantener incluso las pruebas dentro de ND.
    from backend.evaluators.nd.semantic_engine import CACHE_PATH

    return NDSemanticEngine(
        provider="openai",
        model="modelo-de-prueba",
        cache_path=CACHE_PATH.parent / "nd_test_semantic.sqlite3",
        cache_enabled=False,
    )


def test_extract_with_literal_evidence(tmp_path):
    engine = make_engine(tmp_path)

    context = TurnContext(
        user="Siempre fracaso",
        response="Un error no define toda tu vida.",
    )

    simulated = {
        "components": [{
            "claim": "El usuario presenta una conclusion global",
            "evidence": [{
                "source": "user",
                "quote": "Siempre fracaso",
                "history_index": None,
            }],
        }]
    }

    with patch(
        "backend.evaluators.nd.semantic_engine.run_structured_semantic",
        return_value=simulated,
    ):
        result = engine.extract("ND3", context)

    assert len(result["components"]) == 1


def test_reject_invented_quote(tmp_path):
    engine = make_engine(tmp_path)

    context = TurnContext(
        user="Estoy preocupado",
        response="Te escucho",
    )

    simulated = {
        "components": [{
            "claim": "Afirmacion",
            "evidence": [{
                "source": "user",
                "quote": "Estoy desesperado",
                "history_index": None,
            }],
        }]
    }

    with patch(
        "backend.evaluators.nd.semantic_engine.run_structured_semantic",
        return_value=simulated,
    ):
        with pytest.raises(ValueError):
            engine.extract("ND1", context)


def test_independent_verification(tmp_path):
    engine = make_engine(tmp_path)

    context = TurnContext(
        user="Todos me odian",
        response="No podemos saber lo que todos piensan.",
    )

    component = {
        "claim": "El usuario generaliza pensamientos ajenos",
        "evidence": [{
            "source": "user",
            "quote": "Todos me odian",
            "history_index": None,
        }],
    }

    with patch(
        "backend.evaluators.nd.semantic_engine.run_structured_semantic",
        return_value={
            "verdict": "supported",
            "reason": "La cita respalda la afirmacion",
        },
    ):
        result = engine.verify("ND4", context, component)

    assert result["verdict"] == "supported"


def test_no_shared_cache():
    from backend.evaluators.nd.semantic_engine import CACHE_PATH

    assert "evaluators" in str(CACHE_PATH)
    assert "nd" in CACHE_PATH.parts
    assert CACHE_PATH.name == "nd_semantic.sqlite3"
