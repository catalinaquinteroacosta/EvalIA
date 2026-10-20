from backend.evaluators.ir.core import reliable_components


def test_retries_invalid_quote(monkeypatch):
    calls = {"count": 0}

    def fake_extract(*_):
        calls["count"] += 1
        if calls["count"] == 1:
            raise ValueError("Cita no literal")
        return [{"component": "demo"}]

    monkeypatch.setattr(
        reliable_components,
        "extract_components",
        fake_extract,
    )

    monkeypatch.setattr(
        reliable_components,
        "verify_components",
        lambda *_: [{
            "component": "demo",
            "status": "supported",
        }],
    )

    result = reliable_components.evaluate_reliably(
        None, "IR6"
    )

    assert result["attempts"] == 2
    assert result["status"] == "VERIFIED"


def test_exhausted_retries_block(monkeypatch):
    monkeypatch.setattr(
        reliable_components,
        "extract_components",
        lambda *_: (_ for _ in ()).throw(
            ValueError("Cita no literal")
        ),
    )

    result = reliable_components.evaluate_reliably(
        None, "IR6", max_attempts=2
    )

    assert result["status"] == "BLOCKED"
    assert result["score"] is None
    assert result["attempts"] == 2


def test_ambiguous_verification_does_not_retry(monkeypatch):
    calls = {"count": 0}

    def fake_extract(*_):
        calls["count"] += 1
        return [{"component": "demo"}]

    monkeypatch.setattr(
        reliable_components,
        "extract_components",
        fake_extract,
    )

    monkeypatch.setattr(
        reliable_components,
        "verify_components",
        lambda *_: [{
            "component": "demo",
            "status": "BLOCKED",
        }],
    )

    result = reliable_components.evaluate_reliably(
        None, "IR6"
    )

    assert result["status"] == "BLOCKED"
    assert result["attempts"] == 1
    assert calls["count"] == 1
