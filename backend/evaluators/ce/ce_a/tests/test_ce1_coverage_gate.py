import pytest

from backend.evaluators.ce.ce_a.ce1_coverage_gate import (
    assess_ce1_coverage,
)


def audit(verdict, fields=()):
    return {
        "verdict": verdict,
        "findings": [
            {
                "field": field,
                "issue": "Componente no extraido",
                "evidence": "Cita de prueba",
            }
            for field in fields
        ],
        "reason": "Auditoria de prueba.",
    }


def test_complete_approves_ce1():
    result = assess_ce1_coverage(
        audit("complete")
    )
    assert result["approved"] is True


@pytest.mark.parametrize(
    "field",
    [
        "ce2_essential_information_present",
        "ce2_essential_omissions",
        "ce2_unnecessary_overload",
    ],
)
def test_exclusive_ce2_findings_do_not_block_ce1(
    field
):
    result = assess_ce1_coverage(
        audit("incomplete", [field])
    )
    assert result["approved"] is True
    assert len(result["ce2_findings"]) == 1


@pytest.mark.parametrize(
    "field",
    [
        "primary_need",
        "explicit_needs",
        "contextual_needs",
        "ce1_relevant_evidence",
        "ce1_digressions",
    ],
)
def test_ce1_findings_block_ce1(field):
    result = assess_ce1_coverage(
        audit("incomplete", [field])
    )
    assert result["approved"] is False


def test_mixed_findings_block_ce1():
    result = assess_ce1_coverage(
        audit(
            "incomplete",
            [
                "ce1_digressions",
                "ce2_essential_omissions",
            ],
        )
    )
    assert result["approved"] is False
    assert len(result["ce2_findings"]) == 1


def test_ambiguous_audit_blocks_ce1():
    result = assess_ce1_coverage(
        audit("ambiguous")
    )
    assert result["approved"] is False


def test_unknown_field_rejected():
    with pytest.raises(ValueError):
        assess_ce1_coverage(
            audit("incomplete", ["invented_field"])
        )


def test_contradictory_complete_rejected():
    with pytest.raises(ValueError):
        assess_ce1_coverage(
            audit(
                "complete",
                ["ce2_essential_omissions"],
            )
        )
