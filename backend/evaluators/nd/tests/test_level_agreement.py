import pytest

from backend.evaluators.nd.level_agreement import (
    reconcile_level_findings,
)
from backend.evaluators.nd.level_contract import NDLevelFinding
from backend.evaluators.nd.official_rubric import LEVELS


def finding(level, ids=(0,), verdict="supported"):
    return NDLevelFinding(
        indicator="ND7",
        descriptor=LEVELS[level],
        level=level,
        evidence_component_ids=ids,
        verification=verdict,
        reason="Analisis independiente",
    )


@pytest.mark.parametrize("level", ["0", "1", "2", "3"])
def test_agreement_for_each_level(level):
    result = reconcile_level_findings(
        finding(level),
        finding(level),
        confirmed_component_count=1,
    )

    assert result.status == "AGREED"
    assert result.level == level


def test_different_levels_block():
    result = reconcile_level_findings(
        finding("2"),
        finding("3"),
        confirmed_component_count=1,
    )

    assert result.status == "BLOCKED"
    assert result.level is None


def test_ambiguous_blocks():
    result = reconcile_level_findings(
        finding("2", verdict="ambiguous"),
        finding("2"),
        confirmed_component_count=1,
    )

    assert result.status == "BLOCKED"


def test_disjoint_evidence_blocks():
    result = reconcile_level_findings(
        finding("2", ids=(0,)),
        finding("2", ids=(1,)),
        confirmed_component_count=2,
    )

    assert result.status == "BLOCKED"


def test_shared_evidence_agrees():
    result = reconcile_level_findings(
        finding("3", ids=(0, 1)),
        finding("3", ids=(1, 2)),
        confirmed_component_count=3,
    )

    assert result.status == "AGREED"
    assert result.component_ids == (1,)


def test_nonexistent_evidence_rejected():
    with pytest.raises(ValueError):
        reconcile_level_findings(
            finding("3", ids=(5,)),
            finding("3"),
            confirmed_component_count=1,
        )
