
from backend.evaluators.ce.ce_d.ce4_evidence import (
    _resolve_verdict,
)


def test_contradiction_cannot_be_overridden():
    result = _resolve_verdict(
        verify_claim=lambda *args: "not_supported",
        original="Texto completo",
        quote="Texto",
        condition="Condicion",
        component="claim:0",
        reconcile_claim=lambda *args: "supported",
    )
    assert result == "blocked"


def test_ambiguous_can_be_reconciled():
    result = _resolve_verdict(
        verify_claim=lambda *args: "ambiguous",
        original="Texto completo",
        quote="Texto",
        condition="Condicion",
        component="claim:0",
        reconcile_claim=lambda *args: "supported",
    )
    assert result == "supported"


def test_reconciliation_exception_blocks():
    def failing(*args):
        raise RuntimeError("Error")

    result = _resolve_verdict(
        verify_claim=lambda *args: "ambiguous",
        original="Texto completo",
        quote="Texto",
        condition="Condicion",
        component="claim:0",
        reconcile_claim=failing,
    )
    assert result == "blocked"
