
from unittest.mock import patch

import pytest

from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.nd import reconciliation


USER = "Siempre hago todo mal. Nada funciona."
RESPONSE = "Lamento que te sientas asi."


class FakeEngine:
    def __init__(self, verdict, evidence=None, verify="supported"):
        self.verdict = verdict
        self.evidence = evidence if evidence is not None else []
        self.verify_verdict = verify
        self.calls = []
        self.verify_context = None

    def _run(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "verdict": self.verdict,
            "reason": "Condicion examinada",
            "evidence": self.evidence,
        }

    def verify(self, indicator, context, component):
        self.verify_context = context
        return {
            "verdict": self.verify_verdict,
            "reason": "Verificacion independiente",
        }


def recover(engine, indicator="ND7"):
    context = TurnContext(
        user=USER,
        response=RESPONSE,
    )
    result = reconciliation._recover_refuted_absence(
        engine,
        indicator,
        context,
        {"verdict": "present", "reason": "Primera"},
        {"verdict": "absent", "reason": "Segunda"},
        {
            "verdict": "not_supported",
            "reason": "Ausencia refutada",
        },
    )
    return result, engine


def user_evidence():
    return [{
        "source": "user",
        "quote": "Siempre hago todo mal.",
        "history_index": None,
    }]


def test_positive_recovery_verified():
    result, engine = recover(
        FakeEngine("present", user_evidence())
    )
    assert result.status == "APPLICABLE"
    assert engine.verify_context.response == ""


def test_uncertain_remains_blocked():
    result, _ = recover(FakeEngine("uncertain"))
    assert result.status == "BLOCKED"


def test_missing_evidence_remains_blocked():
    result, _ = recover(FakeEngine("present", []))
    assert result.status == "BLOCKED"


def test_response_evidence_is_forbidden():
    result, engine = recover(
        FakeEngine(
            "present",
            [{
                "source": "response",
                "quote": RESPONSE,
                "history_index": None,
            }],
        )
    )
    assert result.status == "BLOCKED"
    assert engine.verify_context is None


def test_independent_rejection_remains_blocked():
    result, _ = recover(
        FakeEngine(
            "present",
            user_evidence(),
            verify="not_supported",
        )
    )
    assert result.status == "BLOCKED"


def test_recovery_stage_is_separate():
    result, engine = recover(
        FakeEngine("present", user_evidence())
    )
    assert engine.calls[0]["stage"] == (
        "recover_refuted_absence"
    )
    assert result.status == "APPLICABLE"
