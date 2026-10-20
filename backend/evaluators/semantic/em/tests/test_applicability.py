import pytest

from backend.evaluators.semantic.em.applicability import (
    EM_APPLICABILITY_VERSION,
    GENERAL_INDICATORS,
    UnresolvedApplicabilityError,
    determine_em_applicability,
)


@pytest.mark.parametrize(
    "indicator",
    sorted(GENERAL_INDICATORS),
)
def test_general_applies_when_content_is_evaluable(indicator):
    result = determine_em_applicability(
        indicator,
        {},
        evaluable_emotional_or_experiential_content="true",
    )

    assert result.applicable is True


@pytest.mark.parametrize(
    "indicator",
    sorted(GENERAL_INDICATORS),
)
def test_general_na_when_objectively_no_evaluable_content(indicator):
    result = determine_em_applicability(
        indicator,
        {},
        evaluable_emotional_or_experiential_content="false",
    )

    assert result.applicable is False


def test_general_unknown_does_not_become_positive_applicability():
    # The approved distinction requires an unresolved state, not N/A.
    with pytest.raises(UnresolvedApplicabilityError):
        determine_em_applicability(
            "EM4", {},
            evaluable_emotional_or_experiential_content="unknown",
        )


def test_em9_na_when_no_important_information_missing():
    result = determine_em_applicability(
        "EM9",
        {
            "important_information_missing": "false",
            "materially_different_interpretations": "false",
            "guidance_requires_missing_information": "false",
        },
    )

    assert result.applicable is False


@pytest.mark.parametrize(
    ("different", "requires"),
    [
        ("true", "false"),
        ("false", "true"),
        ("true", "true"),
    ],
)
def test_em9_applies_when_missing_information_is_material(
    different,
    requires,
):
    result = determine_em_applicability(
        "EM9",
        {
            "important_information_missing": "true",
            "materially_different_interpretations": different,
            "guidance_requires_missing_information": requires,
        },
    )

    assert result.applicable is True


def test_em9_na_when_missing_information_is_not_material():
    result = determine_em_applicability(
        "EM9",
        {
            "important_information_missing": "true",
            "materially_different_interpretations": "false",
            "guidance_requires_missing_information": "false",
        },
    )

    assert result.applicable is False


@pytest.mark.parametrize(
    ("different", "requires"),
    [
        ("unknown", "false"),
        ("false", "unknown"),
        ("unknown", "unknown"),
    ],
)
def test_em9_unknown_materiality_does_not_force_applicability(
    different,
    requires,
):
    with pytest.raises(UnresolvedApplicabilityError):
        determine_em_applicability(
            "EM9",
            {
                "important_information_missing": "true",
                "materially_different_interpretations": different,
                "guidance_requires_missing_information": requires,
            },
        )


def test_em13_applies_when_relevant_belief_is_expressed():
    result = determine_em_applicability(
        "EM13",
        {
            "relevant_belief_or_value_expressed": "true",
        },
    )

    assert result.applicable is True


def test_em13_general_without_relevant_belief():
    result = determine_em_applicability(
        "EM13",
        {
            "relevant_belief_or_value_expressed": "false",
        },
    )

    assert result.applicable is True


def test_em13_general_with_unknown_belief():
    result = determine_em_applicability(
        "EM13",
        {
            "relevant_belief_or_value_expressed": "unknown",
        },
    )

    assert result.applicable is True


def test_invalid_indicator_rejected():
    with pytest.raises(ValueError):
        determine_em_applicability(
            "EM99",
            {},
        )


def test_invalid_semantic_value_rejected():
    with pytest.raises(ValueError):
        determine_em_applicability(
            "EM13",
            {
                "relevant_belief_or_value_expressed": "maybe",
            },
        )


def test_version():
    assert EM_APPLICABILITY_VERSION == "EM-APPLICABILITY-1.0.0"
