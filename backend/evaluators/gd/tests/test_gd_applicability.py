import pytest

from backend.evaluators.gd.gd_applicability import (
    ApplicabilityReview,
    reconcile_applicability,
    validate_reviews,
)


def review(code, verdict):
    return ApplicabilityReview(code, verdict, "Justificación de prueba")


@pytest.mark.parametrize(
    "code",
    ["GD5", "GD7"],
)
def test_applicable_agreement(code):
    assert reconcile_applicability(
        code, "yes", review(code, "applicable")
    ) == "APPLICABLE"


@pytest.mark.parametrize(
    "code",
    ["GD5", "GD7"],
)
def test_na_requires_independent_agreement(code):
    assert reconcile_applicability(
        code, "no", review(code, "not_applicable")
    ) == "NA"


@pytest.mark.parametrize(
    "code",
    ["GD5", "GD7"],
)
def test_disagreement_blocks(code):
    assert reconcile_applicability(
        code, "no", review(code, "applicable")
    ) == "BLOCKED"


@pytest.mark.parametrize(
    "code",
    ["GD5", "GD7"],
)
def test_uncertain_extractor_blocks(code):
    assert reconcile_applicability(
        code, "uncertain", review(code, "applicable")
    ) == "BLOCKED"


@pytest.mark.parametrize(
    "code",
    ["GD5", "GD7"],
)
def test_uncertain_verifier_blocks(code):
    assert reconcile_applicability(
        code, "yes", review(code, "uncertain")
    ) == "BLOCKED"


def test_wrong_indicator_rejected():
    with pytest.raises(ValueError):
        reconcile_applicability(
            "GD5", "yes", review("GD7", "applicable")
        )


def test_general_indicator_rejected():
    with pytest.raises(ValueError):
        reconcile_applicability(
            "GD1", "yes", review("GD5", "applicable")
        )


def test_review_requires_reason():
    with pytest.raises(ValueError):
        ApplicabilityReview("GD5", "applicable", " ")


def test_exact_conditional_coverage():
    validate_reviews((
        review("GD5", "applicable"),
        review("GD7", "not_applicable"),
    ))


def test_duplicate_reviews_rejected():
    with pytest.raises(ValueError):
        validate_reviews((
            review("GD5", "applicable"),
            review("GD5", "applicable"),
        ))
