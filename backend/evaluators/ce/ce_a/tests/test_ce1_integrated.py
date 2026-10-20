from unittest.mock import patch

from backend.evaluators.ce.ce_a import ce1_integrated as mod


def extraction():
    return {
        "primary_need": "Preparar la entrevista.",
        "explicit_needs": [{
            "interpretation": "Preparar la entrevista.",
            "user_evidence": "preparar mi entrevista",
        }],
        "contextual_needs": [],
        "ce1_relevant_evidence": [{
            "interpretation": "Recomienda investigar.",
            "evidence": "Investiga la empresa",
        }],
        "ce1_digressions": [],
        "ce2_essential_information_present": [],
        "ce2_essential_omissions": [],
        "ce2_unnecessary_overload": [],
    }


def run(data=None):
    data = extraction() if data is None else data
    with (
        patch.object(mod, "validate_extraction", return_value=data),
        patch.object(mod, "audit_coverage", return_value={
            "verdict": "complete",
            "findings": [],
            "reason": "Completa.",
        }),
        patch.object(mod, "verify_primary_identity", side_effect=lambda **kw: {
            "verdict": "confirmed" if kw["primary_need"] == kw["candidate_need"] else "rejected",
            "source": "current_user", "evidence": kw["candidate_evidence"],
            "reason": "Identidad simulada para prueba local."
        }),
        patch.object(mod, "verify_need", return_value={
            "verdict": "supported",
            "reason": "Respaldada.",
        }),
        patch.object(mod, "evaluate_verified_need", return_value={
            "coverage": "addressed",
            "severity": None,
            "score": None,
        }),
        patch.object(
            mod,
            "evaluate_verified_digression",
            return_value={
                "status": "verified",
                "decision": {
                    "verified": True,
                    "verdict": "relevant",
                },
                "score": None,
            },
        ),
    ):
        return mod.evaluate_ce1_integrated(
            user_text="Necesito preparar mi entrevista",
            response_text="Investiga la empresa",
            extraction=data,
        )


def test_integrates_without_scoring():
    result = run()
    assert result["status"] == "evidence_integrated"
    assert result["primary_coverage"] == "addressed"
    assert len(result["fragments"]) == 1
    assert result["score"] is None
    assert result["ready_for_scoring"] is False


def test_primary_identity_uncertain_blocks():
    data = extraction()
    data["primary_need"] = "Orientacion profesional."
    result = run(data)
    assert result["status"] == "review_required"
    assert result["primary_coverage"] is None
    assert result["pending"][0]["type"] == (
        "primary_need_identity"
    )


def test_duplicate_fragment_is_not_evaluated_twice():
    data = extraction()
    data["ce1_digressions"] = list(
        data["ce1_relevant_evidence"]
    )
    result = run(data)
    assert len(result["fragments"]) == 1


def test_no_score_even_with_verified_primary():
    result = run()
    assert result["primary_coverage"] == "addressed"
    assert result["severity"] is None
    assert result["score"] is None
