"""Offline checks of selective reconciliation instructions (no network)."""
from backend.evaluators.ps.runner import RECONCILE_SYSTEM

def test_absent_trigger_is_not_automatically_inferred():
    assert "does NOT itself prove 'not_applicable'" in RECONCILE_SYSTEM
    assert 'CURRENT_USER and relevant PRIOR_HISTORY' in RECONCILE_SYSTEM

def test_ambiguity_is_preserved():
    assert 'emit ambiguous' in RECONCILE_SYSTEM
    assert 'Do not choose the highest automatically' in RECONCILE_SYSTEM

def test_positive_evidence_is_required():
    assert 'literal response evidence' in RECONCILE_SYSTEM
