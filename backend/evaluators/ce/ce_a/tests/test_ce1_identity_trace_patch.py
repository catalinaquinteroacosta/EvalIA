"""Regresion de trazabilidad adaptada al contrato de agrupacion CE1."""
from unittest.mock import patch
from backend.evaluators.ce.ce_a import ce1_integrated as mod

def test_two_confirmed_are_traced_and_still_blocked_when_independent():
    extraction = {
        "primary_need": "Agradecer y comunicar mejoria",
        "explicit_needs": [
            {"interpretation": "Agradecer", "user_evidence": "Gracias"},
            {"interpretation": "Comunicar mejoria", "user_evidence": "me siento mejor"},
        ],
        "contextual_needs": [], "ce1_relevant_evidence": [],
        "ce1_digressions": [], "ce2_essential_information_present": [],
        "ce2_essential_omissions": [], "ce2_unnecessary_overload": [],
    }
    with (
        patch.object(mod, "validate_extraction", return_value=extraction),
        patch.object(mod, "audit_coverage", return_value={"verdict": "complete", "findings": [], "reason": "ok"}),
        patch.object(mod, "verify_primary_identity", side_effect=lambda **kw: {
            "verdict": "confirmed", "source": "current_user",
            "evidence": kw["candidate_evidence"], "reason": "test"
        }),
        patch.object(mod, "verify_primary_group", return_value={
            "verdict": "independent", "member_indices": [], "reason": "test"
        }) as group,
    ):
        result = mod.evaluate_ce1_integrated(
            user_text="Gracias, me siento mejor", response_text="Me alegra", extraction=extraction
        )
    group.assert_called_once()
    assert result["status"] == "review_required"
    assert result["score"] is None
    assert len(result["primary_identity_trace"]) == 2
    assert [x["verification"]["verdict"] for x in result["primary_identity_trace"]] == ["confirmed", "confirmed"]
    assert any(item["type"] == "primary_group_unresolved" for item in result["pending"])
