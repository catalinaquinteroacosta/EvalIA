import pytest

from backend.evaluators.cp.applicability import (
    cp6_applicability,
)
from backend.evaluators.cp.schemas import CP6SemanticState
from backend.evaluators.cp.validated_state import (
    ValidatedIndicatorState,
)


def make_cp6(needed: bool, used: bool):
    return CP6SemanticState(
        example_or_analogy_needed=needed,
        example_or_analogy_used=used,
        pertinence="none",
        clarification_value="none",
        distortion_present=False,
        trivialization_present=False,
        concrete_secondary_limitation=False,
        claims=(),
    )



@pytest.mark.parametrize(
    "needed, used, expected",
    [
        (False, False, "not_applicable"),
        (False, True, "not_applicable"),
        (True, False, "applicable"),
        (True, True, "applicable"),
    ],
)
def test_cp6_applicability_matches_official_contract(
    needed,
    used,
    expected,
):
    decision = cp6_applicability(
        make_cp6(needed, used)
    )

    assert decision.state == expected


def test_blocked_may_be_caused_by_evidence_only():
    state = ValidatedIndicatorState(
        code="CP1",
        status="blocked",
        components={
            "central_problem_identification": "complete",
            "secondary_concerns_present": False,
            "secondary_concerns_coverage": "complete",
            "substitution_or_unfounded_problem": False,
            "concrete_secondary_limitation": False,
        },
        blocked_components=(),
        supported_evidence_indices=(0,),
        blocked_evidence_indices=(1,),
    )

    assert state.status == "blocked"
    assert not state.ready_for_scoring


def test_validated_cannot_contain_blocked_evidence():
    with pytest.raises(ValueError):
        ValidatedIndicatorState(
            code="CP1",
            status="validated",
            components={
                "central_problem_identification": "complete",
                "secondary_concerns_present": False,
                "secondary_concerns_coverage": "complete",
                "substitution_or_unfounded_problem": False,
                "concrete_secondary_limitation": False,
            },
            blocked_components=(),
            supported_evidence_indices=(0,),
            blocked_evidence_indices=(1,),
        )
