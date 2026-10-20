import pytest

from backend.evaluators.ir.core.contracts import Context
from backend.evaluators.ir.core import semantic
from backend.evaluators.ir.core import verify as verifier
from backend.evaluators.ir import runner


def test_eight_indicators():
    assert list(semantic.INDICATORS) == [
        "IR1", "IR2", "IR3", "IR4",
        "IR5", "IR6", "IR7", "IR8"
    ]


def test_extractor_no_scoring(monkeypatch):
    def fake(system, payload):
        return {"indicators": {
            k: [] for k in semantic.INDICATORS
        }}
    monkeypatch.setattr(semantic, "ask_openai", fake)
    ctx = Context("Hola", "Hola")
    result = semantic.extract(ctx)
    assert len(result) == 8


def test_reject_fabricated_quote(monkeypatch):
    def fake(system, payload):
        data = {k: [] for k in semantic.INDICATORS}
        data["IR1"] = [{
            "claim": "Reconoce pensamiento",
            "evidence": [{
                "source": "response",
                "quote": "Cita inexistente",
                "history_index": None
            }],
            "limitations": []
        }]
        return {"indicators": data}
    monkeypatch.setattr(semantic, "ask_openai", fake)
    with pytest.raises(ValueError):
        semantic.extract(Context("Hola", "Hola"))


def test_reject_user_only_evidence(monkeypatch):
    def fake(system, payload):
        data = {k: [] for k in semantic.INDICATORS}
        data["IR1"] = [{
            "claim": "Reconoce pensamiento",
            "evidence": [{
                "source": "user",
                "quote": "Me preocupa",
                "history_index": None
            }],
            "limitations": []
        }]
        return {"indicators": data}
    monkeypatch.setattr(semantic, "ask_openai", fake)
    with pytest.raises(ValueError):
        semantic.extract(
            Context("Me preocupa", "Entiendo")
        )


def test_verifier_rejects_bad_status(monkeypatch):
    monkeypatch.setattr(
        verifier, "ask_openai",
        lambda system, payload: {
            "results": [{
                "status": "3",
                "reason": "Incorrecto"
            }]
        }
    )
    with pytest.raises(ValueError):
        verifier.verify(
            Context("Hola", "Hola"), "IR1",
            [{"claim": "Algo", "evidence": []}]
        )


def test_runner_no_scores(monkeypatch):
    monkeypatch.setattr(
        runner, "extract",
        lambda ctx: {
            k: [] for k in semantic.INDICATORS
        }
    )
    result = runner.run(Context("Hola", "Hola"))
    assert len(result["indicators"]) == 8
    assert all(
        v["score"] is None
        for v in result["indicators"].values()
    )


def test_runner_blocks_ambiguity(monkeypatch):
    monkeypatch.setattr(
        runner, "extract",
        lambda ctx: {
            k: ([{"claim": "X"}] if k == "IR1" else [])
            for k in semantic.INDICATORS
        }
    )
    monkeypatch.setattr(
        runner, "verify",
        lambda ctx, key, claims: (
            [{"verification": "ambiguous"}]
            if claims else []
        )
    )
    result = runner.run(Context("Hola", "Hola"))
    assert result["indicators"]["IR1"]["status"] == "BLOCKED"
    assert result["indicators"]["IR2"]["status"] == "EXTRACTED"