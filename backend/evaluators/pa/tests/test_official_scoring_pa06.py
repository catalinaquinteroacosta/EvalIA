from backend.evaluators.pa.official_scoring_pa import score_verified

def test_pa_level_without_evidence_is_blocked():
    result = score_verified(
        "PA1",
        level=3,
        verified=True,
        applicability="applicable",
    )
    assert result["status"] == "BLOCKED"

def test_pa_level_without_independent_verification_is_blocked():
    result = score_verified(
        "PA1",
        level=3,
        verified=True,
        applicability="applicable",
        level_evidence={
            "quotes": ["Puedes elegir una tarea"],
            "reason": "Accion propuesta",
        },
    )
    assert result["status"] == "BLOCKED"

def test_pa_general_cannot_be_na():
    result = score_verified(
        "PA4",
        verified=True,
        applicability="not_applicable",
    )
    assert result["status"] == "BLOCKED"

def test_pa_conditional_can_be_na():
    result = score_verified(
        "PA2",
        verified=True,
        applicability="not_applicable",
    )
    assert result["status"] == "N/A"

def test_pa_unresolved_remains_blocked():
    result = score_verified(
        "PA7",
        level=3,
        verified=True,
        applicability="applicable",
        unresolved=True,
    )
    assert result["status"] == "BLOCKED"
