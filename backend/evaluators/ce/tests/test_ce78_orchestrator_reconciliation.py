
from backend.evaluators.ce.pilot import integrate_ce6_ce8


def extraction(quote):
    return {
        "analysis_complete": True,
        "full_response_audited": True,
        "applicable": True,
        "contradiction_impact": "major",
        "claims": [
            {
                "source": "response",
                "quote": quote,
                "interpretation": "Recomienda elegir el momento",
            }
        ],
    }


def test_ce7_recovery_then_independent_verification(monkeypatch):
    calls = []

    def extract_runner(**kwargs):
        calls.append("extract")
        return extraction("elige el momento")

    def repair_runner(**kwargs):
        calls.append("repair")
        return {
            "quote": "elegir el momento",
            "interpretation": "Recomienda elegir el momento",
        }

    def semantic_runner(**kwargs):
        if "REEXTRACCION" in kwargs["prompt"]:
            return repair_runner(**kwargs)
        return extract_runner(**kwargs)

    def verify_claim(source, quote, interpretation):
        calls.append("verify")
        return "supported"

    result = integrate_ce6_ce8.evaluate(
        indicator="CE7",
        user_text="Pregunta",
        response_text="Intenta elegir el momento.",
        semantic_runner=semantic_runner,
        verify_claim=verify_claim,
    )

    assert calls[:2] == ["extract", "repair"]
    assert "verify" in calls
    assert result["status"] == "scored"


def test_ce7_unresolved_repair_never_scores():
    def semantic_runner(**kwargs):
        if "REEXTRACCION" in kwargs["prompt"]:
            return {
                "quote": "elige el momento",
                "interpretation": "Recomienda elegir el momento",
            }
        return extraction("elige el momento")

    def verifier(*args):
        raise AssertionError("No debe verificarse")

    result = integrate_ce6_ce8.evaluate(
        indicator="CE7",
        user_text="Pregunta",
        response_text="Intenta elegir el momento.",
        semantic_runner=semantic_runner,
        verify_claim=verifier,
    )

    assert result["status"] == "BLOCKED"
    assert result["score"] is None


def test_ce6_does_not_use_reconciliation(monkeypatch):
    def fake_extract(**kwargs):
        return {
            "status": "unverified_draft",
            "identity": "test",
            "extraction": {},
        }

    class Bridge:
        extract_ce6_draft = staticmethod(fake_extract)

        @staticmethod
        def evaluate_ce6_with_verifier(**kwargs):
            return {"status": "insufficient_evidence", "score": None}

    original_import = integrate_ce6_ce8.import_module

    def patched_import(name):
        if name.endswith("ce6_provider_bridge"):
            return Bridge
        return original_import(name)

    monkeypatch.setattr(
        integrate_ce6_ce8,
        "import_module",
        patched_import,
    )

    result = integrate_ce6_ce8.evaluate(
        indicator="CE6",
        user_text="Pregunta",
        response_text="Respuesta",
        semantic_runner=lambda **kwargs: {},
        verify_claim=lambda *args: "supported",
    )

    assert result["status"] == "insufficient_evidence"
