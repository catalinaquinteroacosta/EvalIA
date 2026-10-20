
import pytest

from backend.evaluators.cp.verifier import CP_COMPONENT_FIELDS
from backend.evaluators.cp.validated_state import (
    ValidatedIndicatorState,
)
from backend.evaluators.cp.rejected_evidence import (
    exclude_rejected_evidence,
)


def make_state():
    # Respetar la cobertura completa del contrato CP5.
    fields = CP_COMPONENT_FIELDS["cp5"]
    assert "knowledge_support" in fields

    return ValidatedIndicatorState(
        code="cp5",
        status="blocked",
        components={},
        blocked_components=tuple(fields),
        supported_evidence_indices=(),
        blocked_evidence_indices=(0,),
    )


def test_rejected_evidence_keeps_component_blocked():
    verification = {
        "evidence_verdicts": [{
            "evidence_index": 0,
            "status": "unsupported",
            "reason": "La cita no respalda el constructo.",
        }]
    }

    state, audit = exclude_rejected_evidence(
        make_state(), verification, (0,)
    )

    assert state.status == "blocked"
    assert state.blocked_evidence_indices == ()
    assert set(state.blocked_components) == set(
        CP_COMPONENT_FIELDS["cp5"]
    )
    assert len(audit) == 1
    assert audit[0]["reason"]


@pytest.mark.parametrize(
    "status", ["supported", "ambiguous"]
)
def test_cannot_exclude_non_rejected_evidence(status):
    verification = {
        "evidence_verdicts": [{
            "evidence_index": 0,
            "status": status,
            "reason": "Sin rechazo expl?cito.",
        }]
    }

    with pytest.raises(ValueError):
        exclude_rejected_evidence(
            make_state(), verification, (0,)
        )


def test_missing_reason_fails_closed():
    verification = {
        "evidence_verdicts": [{
            "evidence_index": 0,
            "status": "unsupported",
            "reason": "",
        }]
    }

    with pytest.raises(ValueError):
        exclude_rejected_evidence(
            make_state(), verification, (0,)
        )


def test_cannot_exclude_unknown_index():
    with pytest.raises(ValueError):
        exclude_rejected_evidence(
            make_state(),
            {"evidence_verdicts": []},
            (7,),
        )
