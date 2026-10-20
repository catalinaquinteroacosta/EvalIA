import pytest

from backend.evaluators.nd.level_contract import (
    NDLevelFinding,
    validate_level_finding,
)
from backend.evaluators.nd.official_rubric import LEVELS


def finding(level="2", verification="supported", ids=(0,)):
    return NDLevelFinding(
        indicator="ND7",
        descriptor=LEVELS[level],
        level=level,
        evidence_component_ids=ids,
        verification=verification,
        reason="Correspondencia revisada",
    )


@pytest.mark.parametrize("level", ["0", "1", "2", "3"])
def test_official_descriptor_accepted(level):
    assert validate_level_finding(
        finding(level=level),
        confirmed_component_count=1,
    )


def test_modified_descriptor_rejected():
    item = NDLevelFinding(
        indicator="ND7",
        descriptor="Descriptor inventado",
        level="3",
        evidence_component_ids=(0,),
        verification="supported",
        reason="Revision",
    )

    with pytest.raises(ValueError):
        validate_level_finding(item, 1)


@pytest.mark.parametrize(
    "verification",
    ["not_supported", "ambiguous"],
)
def test_unverified_level_not_accepted(verification):
    assert not validate_level_finding(
        finding(verification=verification),
        1,
    )


def test_missing_evidence_not_accepted():
    assert not validate_level_finding(
        finding(ids=()),
        1,
    )


def test_nonexistent_component_rejected():
    with pytest.raises(ValueError):
        validate_level_finding(
            finding(ids=(3,)),
            1,
        )


def test_duplicate_component_rejected():
    with pytest.raises(ValueError):
        validate_level_finding(
            finding(ids=(0, 0)),
            1,
        )
