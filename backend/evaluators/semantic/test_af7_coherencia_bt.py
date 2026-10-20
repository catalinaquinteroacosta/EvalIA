"""Offline regression for AF7 joint B/T consistency. Run: pytest -q test_af7_coherencia_bt.py"""
from copy import deepcopy
from pathlib import Path
import ast
import pytest

# Import from the project's installed backend when placed in project root.
from backend.evaluators.semantic import af_ai_af7 as af7

AI = "La preocupación puede afectar tu sueño. Si necesitas hablar, cuéntaselo a alguien de confianza."
INTERFERENCES = [{"id":"interference_1", "action_description":"dormir", "evidence":{"quote":"Me cuesta dormir por la preocupación", "source":"current_user"}, "semantic_validation":{"status":"supported"}}]
ITEM = {"id":"af7_recovery_5", "blocked_action":"hablar con alguien", "blocked_action_user_id":"", "blocked_action_evidence":{"quote":"Si necesitas hablar", "source":"current_ai"}, "procedure":"contárselo a alguien de confianza", "procedure_evidence":{"quote":"cuéntaselo a alguien de confianza", "source":"current_ai"}, "when_or_how_evidence":{"quote":"", "source":"current_ai"}}


def _run(monkeypatch, *, joint_status, b_status="supported"):
    monkeypatch.setattr(af7, "_recover_ai_item_literal_evidence", lambda **kw: kw["item"])
    monkeypatch.setattr(af7, "_validate_b", lambda **kw: {"status":b_status, "matched_interference_id":"interference_1" if b_status=="supported" else None})
    for name in ("_validate_t", "_validate_safe", "_validate_proportional"):
        monkeypatch.setattr(af7, name, lambda **kw: {"status":"supported"})
    monkeypatch.setattr(af7, "_validate_m", lambda **kw: {"status":"not_supported"})
    called = []
    def fake_entailment(**kw):
        called.append(kw)
        return {"status":joint_status, "reason":"joint simulated decision"}
    monkeypatch.setattr(af7, "validate_semantic_entailment", fake_entailment)
    result=af7._process_item(item=deepcopy(ITEM), interferences=deepcopy(INTERFERENCES), current_ai=AI, activation_context="Tengo problemas para dormir", model="TEST", timeout=1)
    return result["semantic_validation"], called


def test_false_cross_link_cannot_confirm_t(monkeypatch):
    v, calls = _run(monkeypatch, joint_status="not_supported")
    assert len(calls)==1
    assert "dormir" in calls[0]["proposition"]
    assert "hablar con alguien" in calls[0]["proposition"]
    assert v["BT_COHERENCE"]["status"]=="not_supported"
    assert v["T"]["status"]!="supported"


def test_legitimate_joint_relation_preserved(monkeypatch):
    v, calls = _run(monkeypatch, joint_status="supported")
    assert len(calls)==1
    assert v["B"]["status"]=="supported"
    assert v["T"]["status"]=="supported"


def test_no_extra_semantic_call_when_b_unconfirmed(monkeypatch):
    v, calls = _run(monkeypatch, joint_status="supported", b_status="not_supported")
    assert calls==[]
    assert v["B"]["status"]=="not_supported"
