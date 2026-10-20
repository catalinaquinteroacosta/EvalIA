from backend.evaluators.pa.scoring_guard import (
    PropertyRecord,
    check_scoring_readiness,
)


def valid_property():
    return PropertyRecord(
        name="accion observable",
        value="present",
        verified=True,
        evidence_valid=True,
    )


def test_verified_properties_do_not_produce_score():
    result = check_scoring_readiness(
        "PA1", True, (valid_property(),)
    )
    assert result.status == "READY_FOR_RULE_MAPPING"
    assert result.score is None


def test_discrepancy_blocks():
    result = check_scoring_readiness(
        "PA7", True, (valid_property(),),
        unresolved_discrepancy=True,
    )
    assert result.status == "BLOCKED"


def test_unverified_property_blocks():
    property_record = PropertyRecord(
        "finalidad explicada", "present", False, True
    )
    result = check_scoring_readiness(
        "PA7", True, (property_record,)
    )
    assert result.status == "BLOCKED"


def test_missing_evidence_blocks():
    property_record = PropertyRecord(
        "accion observable", "present", True, False
    )
    result = check_scoring_readiness(
        "PA1", True, (property_record,)
    )
    assert result.status == "BLOCKED"


def test_uncertainty_blocks():
    property_record = PropertyRecord(
        "accion observable", "uncertain", True, True
    )
    result = check_scoring_readiness(
        "PA1", True, (property_record,)
    )
    assert result.status == "BLOCKED"
