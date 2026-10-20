
from backend.evaluators.ps.semantic import VERIFY_SYSTEM
from backend.evaluators.ps.runner import RECONCILE_SYSTEM


def test_applicability_excludes_response():
    assert "NEVER the evaluated response alone" in VERIFY_SYSTEM
    assert "ignore CURRENT_RESPONSE" in RECONCILE_SYSTEM


def test_absence_can_support_na():
    assert "supports not_applicable" in VERIFY_SYSTEM
    assert "empty evidence allowed" in RECONCILE_SYSTEM


def test_reconciliation_checks_both_predicates():
    assert "BOTH propositions" in RECONCILE_SYSTEM
    assert "independently inspect" in RECONCILE_SYSTEM


def test_levels_are_exclusive():
    assert "EXCLUSIVE FINAL outcome" in VERIFY_SYSTEM
    assert "mutually exclusive" in RECONCILE_SYSTEM


def test_level_conflict_requires_full_rubric():
    assert "COMPLETE level 2 and 3 rubric anchors" in RECONCILE_SYSTEM
    assert "Do not choose the highest automatically" in RECONCILE_SYSTEM


def test_reconciliation_preserves_validated_work():
    assert "do not change unrelated verified propositions" in RECONCILE_SYSTEM
    assert "Never force a grade" in RECONCILE_SYSTEM
