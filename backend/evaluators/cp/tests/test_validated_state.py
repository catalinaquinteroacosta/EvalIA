from copy import deepcopy

import pytest

from backend.evaluators.cp.validated_state import (
    ValidatedIndicatorState,
    build_validated_indicator_state,
    build_validated_cp_family_state,
)
from backend.evaluators.cp.verifier import (
    CP_COMPONENT_FIELDS,
)


def make_draft_indicator(code):
    values = {}

    for field in CP_COMPONENT_FIELDS[code]:
        if field == "concrete_secondary_limitation":
            values[field] = False
        elif (
            field.endswith("_present")
            or field.startswith("structural_")
            or field.startswith("serious_")
            or field.startswith("direct_")
            or field.startswith("correction_")
            or field.startswith("generic_")
            or field.startswith("unnecessary_")
            or field.startswith("indispensable_technical_")
            or field.startswith("unsupported_")
            or field.startswith("speculation_")
            or field.startswith("diagnosis_")
            or field.startswith("responsible_")
            or field.startswith("materially_")
            or field.startswith("distortion_")
            or field.startswith("trivialization_")
            or field.startswith("example_or_analogy_")
            or field.startswith("substitution_")
        ):
            values[field] = False
        else:
            values[field] = "complete"

    values.update(
        {
            "analysis_complete": True,
            "full_response_audited": True,
            "limitation_description": "",
            "evidence": [],
        }
    )

    return values


def make_verification_indicator(
    code,
    overrides=None,
):
    overrides = overrides or {}

    verdicts = []

    for field in CP_COMPONENT_FIELDS[code]:
        verdicts.append(
            {
                "field": field,
                "status": overrides.get(
                    field,
                    "supported",
                ),
                "reason": "test",
            }
        )

    return {
        "analysis_complete": True,
        "full_context_audited": True,
        "component_verdicts": verdicts,
        "evidence_verdicts": [],
    }


def make_family():
    draft = {
        "analysis_complete": True,
    }

    verification = {
        "analysis_complete": True,
    }

    for code in CP_COMPONENT_FIELDS:
        draft[code] = make_draft_indicator(code)
        verification[code] = (
            make_verification_indicator(code)
        )

    return draft, verification


def test_supported_component_passes_exact_value():
    draft = make_draft_indicator("cp3")
    verification = make_verification_indicator(
        "cp3"
    )

    state = build_validated_indicator_state(
        code="cp3",
        draft_indicator=draft,
        verification_indicator=verification,
    )

    assert state.status == "validated"
    assert state.ready_for_scoring is True

    for field in CP_COMPONENT_FIELDS["cp3"]:
        assert state.components[field] == draft[field]


@pytest.mark.parametrize(
    "status",
    [
        "unsupported",
        "ambiguous",
    ],
)
def test_non_supported_component_is_blocked(
    status,
):
    draft = make_draft_indicator("cp3")

    verification = make_verification_indicator(
        "cp3",
        {
            "organization_quality": status,
        },
    )

    state = build_validated_indicator_state(
        code="cp3",
        draft_indicator=draft,
        verification_indicator=verification,
    )

    assert state.status == "blocked"
    assert state.ready_for_scoring is False

    assert (
        "organization_quality"
        in state.blocked_components
    )

    assert (
        "organization_quality"
        not in state.components
    )


def test_unsupported_is_not_converted_to_false():
    draft = make_draft_indicator("cp5")

    draft["diagnosis_presented_as_fact"] = True

    verification = make_verification_indicator(
        "cp5",
        {
            "diagnosis_presented_as_fact":
                "unsupported",
        },
    )

    state = build_validated_indicator_state(
        code="cp5",
        draft_indicator=draft,
        verification_indicator=verification,
    )

    assert (
        "diagnosis_presented_as_fact"
        not in state.components
    )

    assert (
        "diagnosis_presented_as_fact"
        in state.blocked_components
    )


def test_ambiguous_is_not_converted_to_none():
    draft = make_draft_indicator("cp3")
    draft["organization_quality"] = "none"

    verification = make_verification_indicator(
        "cp3",
        {
            "organization_quality":
                "ambiguous",
        },
    )

    state = build_validated_indicator_state(
        code="cp3",
        draft_indicator=draft,
        verification_indicator=verification,
    )

    assert (
        "organization_quality"
        not in state.components
    )


def test_one_blocked_indicator_does_not_block_family():
    draft, verification = make_family()

    verification["cp3"] = (
        make_verification_indicator(
            "cp3",
            {
                "organization_quality":
                    "unsupported",
            },
        )
    )

    family = build_validated_cp_family_state(
        draft=draft,
        verification=verification,
    )

    assert family.readiness["CP3"] is False

    for code in [
        "CP1",
        "CP2",
        "CP4",
        "CP5",
        "CP6",
        "CP7",
        "CP8",
    ]:
        assert family.readiness[code] is True


def test_supported_and_blocked_evidence_partition():
    draft = make_draft_indicator("cp1")

    verification = make_verification_indicator(
        "cp1"
    )

    verification["evidence_verdicts"] = [
        {
            "evidence_index": 0,
            "status": "supported",
            "reason": "ok",
        },
        {
            "evidence_index": 1,
            "status": "ambiguous",
            "reason": "unclear",
        },
        {
            "evidence_index": 2,
            "status": "unsupported",
            "reason": "no",
        },
    ]

    state = build_validated_indicator_state(
        code="cp1",
        draft_indicator=draft,
        verification_indicator=verification,
    )

    assert (
        state.supported_evidence_indices
        == (0,)
    )

    assert (
        state.blocked_evidence_indices
        == (1, 2)
    )


def test_duplicate_component_verdict_fails_closed():
    draft = make_draft_indicator("cp1")

    verification = make_verification_indicator(
        "cp1"
    )

    verification["component_verdicts"].append(
        deepcopy(
            verification[
                "component_verdicts"
            ][0]
        )
    )

    with pytest.raises(ValueError):
        build_validated_indicator_state(
            code="cp1",
            draft_indicator=draft,
            verification_indicator=verification,
        )


def test_missing_component_verdict_fails_closed():
    draft = make_draft_indicator("cp1")

    verification = make_verification_indicator(
        "cp1"
    )

    verification[
        "component_verdicts"
    ].pop()

    with pytest.raises(ValueError):
        build_validated_indicator_state(
            code="cp1",
            draft_indicator=draft,
            verification_indicator=verification,
        )


def test_invalid_status_fails_closed():
    draft = make_draft_indicator("cp1")

    verification = make_verification_indicator(
        "cp1"
    )

    verification[
        "component_verdicts"
    ][0]["status"] = "maybe"

    with pytest.raises(ValueError):
        build_validated_indicator_state(
            code="cp1",
            draft_indicator=draft,
            verification_indicator=verification,
        )


def test_family_requires_all_cp_codes():
    draft, verification = make_family()

    del verification["cp8"]

    with pytest.raises(ValueError):
        build_validated_cp_family_state(
            draft=draft,
            verification=verification,
        )


def test_validated_state_rejects_overlap():
    with pytest.raises(ValueError):
        ValidatedIndicatorState(
            code="cp1",
            status="blocked",
            components={
                field: "complete"
                for field
                in CP_COMPONENT_FIELDS["cp1"]
            },
            blocked_components=(
                "central_problem_identification",
            ),
            supported_evidence_indices=(),
            blocked_evidence_indices=(),
        )
