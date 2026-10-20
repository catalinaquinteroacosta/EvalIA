
from copy import deepcopy

from backend.evaluators.ce.pilot.ce78_reconciliation import (
    reconcile_literal_claims,
)


def draft(quote):
    return {
        "analysis_complete": True,
        "full_response_audited": True,
        "applicable": True,
        "contradiction_impact": "major",
        "claims": [{
            "source": "response",
            "quote": quote,
            "interpretation": "Recomienda elegir el momento",
        }],
    }


def run(extraction, runner):
    return reconcile_literal_claims(
        indicator="CE7",
        user_text="Pregunta",
        response_text="Intenta elegir el momento.",
        extraction=extraction,
        semantic_runner=runner,
    )


def test_exact_evidence_requires_no_repair():
    calls = []

    def runner(**kwargs):
        calls.append(kwargs)
        raise AssertionError("No debe llamarse")

    result = run(draft("elegir el momento"), runner)

    assert result["status"] == "ready_for_verification"
    assert calls == []


def test_repair_produces_exact_quote():
    original = draft("elige el momento")
    before = deepcopy(original)

    def runner(**kwargs):
        return {
            "quote": "elegir el momento",
            "interpretation":
                "Recomienda elegir el momento",
        }

    result = run(original, runner)

    assert result["status"] == "ready_for_verification"
    assert result["repaired_indices"] == [0]
    assert original == before
    assert (
        result["extraction"]["claims"][0]["quote"]
        == "elegir el momento"
    )


def test_nonliteral_repair_is_blocked():
    def runner(**kwargs):
        return {
            "quote": "elige el momento",
            "interpretation":
                "Recomienda elegir el momento",
        }

    result = run(draft("elige el momento"), runner)

    assert result["status"] == "BLOCKED"
    assert result["score"] is None


def test_changed_interpretation_is_blocked():
    def runner(**kwargs):
        return {
            "quote": "elegir el momento",
            "interpretation": "Otra interpretacion",
        }

    result = run(draft("elige el momento"), runner)

    assert result["status"] == "BLOCKED"


def test_runner_failure_is_blocked():
    def runner(**kwargs):
        raise RuntimeError("Fallo simulado")

    result = run(draft("elige el momento"), runner)

    assert result["status"] == "BLOCKED"
    assert result["score"] is None


def test_missing_runner_is_blocked():
    result = run(draft("elige el momento"), None)

    assert result["status"] == "BLOCKED"
    assert result["score"] is None
