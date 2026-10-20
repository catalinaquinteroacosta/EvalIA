from backend.evaluators.pa.finalize_pa64 import (
    consolidate, criterion_ready
)


def test_accepted_reconciliation():
    original = {"CASE:PA4": {"state": "BLOCKED"}}
    decisions = {
        "CASE:PA4": {"decision": "SUPPORTED"}
    }

    result = consolidate(original, decisions)
    assert result["CASE:PA4"]["state"] == "SUPPORTED"


def test_blocked_remains_blocked():
    original = {"CASE:PA4": {"state": "BLOCKED"}}
    decisions = {
        "CASE:PA4": {"decision": "BLOCKED"}
    }

    result = consolidate(original, decisions)
    assert result["CASE:PA4"]["state"] == "BLOCKED"


def test_criterion_not_ready_with_blocked():
    assert not criterion_ready({
        "CASE:PA1": {"state": "SUPPORTED"},
        "CASE:PA2": {"state": "BLOCKED"},
    })


def test_criterion_ready_without_blocked():
    assert criterion_ready({
        "CASE:PA1": {"state": "SUPPORTED"},
        "CASE:PA2": {"state": "N/A"},
    })
