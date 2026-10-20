from backend.evaluators.ir.core import reliable_components


def test_ir21_normalizes_accents():
    assert reliable_components.normalize_error(
        "N\u00famero de componentes incorrecto"
    ) == "numero de componentes incorrecto"


def test_ir21_retries_real_ir1_error(monkeypatch):
    calls = {"count": 0}

    def extract(ctx, code):
        calls["count"] += 1
        raise ValueError(
            "N\u00famero de componentes incorrecto"
        )

    monkeypatch.setattr(
        reliable_components,
        "extract_components",
        extract,
    )

    result = reliable_components.evaluate_reliably(
        object(), "IR1", max_attempts=2
    )

    assert calls["count"] == 2
    assert result["status"] == "BLOCKED"
    assert result["attempts"] == 2
    assert len(result["errors"]) == 2
    assert result["reason"] == (
        "No se obtuvo un contrato semantico valido"
    )


def test_ir21_does_not_hide_unknown_errors(monkeypatch):
    def extract(ctx, code):
        raise ValueError("Fallo desconocido")

    monkeypatch.setattr(
        reliable_components,
        "extract_components",
        extract,
    )

    try:
        reliable_components.evaluate_reliably(
            object(), "IR1"
        )
    except ValueError as exc:
        assert str(exc) == "Fallo desconocido"
    else:
        raise AssertionError(
            "Se oculto una excepcion desconocida"
        )
