import pytest

from backend.evaluators.ir.core import reliable_components


def test_ir18_retries_component_count(monkeypatch):
    calls = {"count": 0}

    def extract(ctx, code):
        calls["count"] += 1

        if calls["count"] == 1:
            raise ValueError(
                "N\u00famero de componentes incorrecto"
            )

        return [{"component": "test"}]

    def verify(ctx, code, extracted):
        return [{
            "component": "test",
            "status": "supported",
        }]

    monkeypatch.setattr(
        reliable_components,
        "extract_components",
        extract,
    )

    monkeypatch.setattr(
        reliable_components,
        "verify_components",
        verify,
    )

    result = reliable_components.evaluate_reliably(
        object(), "IR1", max_attempts=2
    )

    assert result["status"] == "VERIFIED"
    assert result["attempts"] == 2
    assert result["errors"][0]["detail"] == (
        "N\u00famero de componentes incorrecto"
    )


def test_ir18_preserves_literal_error(monkeypatch):
    def extract(ctx, code):
        raise ValueError("Cita no literal")

    monkeypatch.setattr(
        reliable_components,
        "extract_components",
        extract,
    )

    result = reliable_components.evaluate_reliably(
        object(), "IR3", max_attempts=2
    )

    assert result["status"] == "BLOCKED"
    assert len(result["errors"]) == 2
    assert all(
        item["detail"] == "Cita no literal"
        for item in result["errors"]
    )
