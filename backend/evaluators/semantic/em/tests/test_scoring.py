import pytest

from backend.evaluators.semantic.em.scorer import (
    EM_SCORER_VERSION,
    EMScoreResult,
    UnresolvedScoringState,
    VerifiedSemanticValue,
    na_result,
    numeric_result,
    require_resolved,
    score_em_indicator,
    verified_values_from_pipeline,
)


def _value(
    name="x",
    proposed="true",
    status="supported",
):
    return VerifiedSemanticValue(
        name=name,
        proposed_value=proposed,
        verification_status=status,
    )


def test_version():
    assert EM_SCORER_VERSION == "EM-SCORER-1.6.1"


def test_supported_true_resolves_true():
    value = _value(
        proposed="true",
        status="supported",
    )

    assert value.resolved_value == "true"


def test_supported_false_resolves_false():
    value = _value(
        proposed="false",
        status="supported",
    )

    assert value.resolved_value == "false"


def test_supported_unknown_remains_unknown():
    value = _value(
        proposed="unknown",
        status="supported",
    )

    assert value.resolved_value == "unknown"


@pytest.mark.parametrize(
    "status",
    [
        "unsupported",
        "ambiguous",
    ],
)
def test_non_supported_claim_never_becomes_opposite_fact(status):
    value = _value(
        proposed="true",
        status=status,
    )

    assert value.resolved_value == "unknown"


def test_unsupported_false_does_not_become_true():
    value = _value(
        proposed="false",
        status="unsupported",
    )

    assert value.resolved_value == "unknown"


def test_invalid_semantic_value_rejected():
    with pytest.raises(ValueError):
        _value(
            proposed="maybe",
        )


def test_invalid_verification_status_rejected():
    with pytest.raises(ValueError):
        _value(
            status="probably",
        )


def test_pipeline_join_preserves_supported_value():
    values = verified_values_from_pipeline(
        components={
            "emotion_recognized": {
                "value": "true",
            },
        },
        verifications={
            "emotion_recognized": {
                "status": "supported",
            },
        },
    )

    assert (
        values["emotion_recognized"].resolved_value
        == "true"
    )


def test_pipeline_join_preserves_ambiguity_as_unknown():
    values = verified_values_from_pipeline(
        components={
            "emotion_recognized": {
                "value": "true",
            },
        },
        verifications={
            "emotion_recognized": {
                "status": "ambiguous",
            },
        },
    )

    assert (
        values["emotion_recognized"].resolved_value
        == "unknown"
    )


def test_pipeline_join_rejects_missing_verification():
    with pytest.raises(ValueError):
        verified_values_from_pipeline(
            components={
                "a": {
                    "value": "true",
                },
            },
            verifications={},
        )


def test_require_resolved_accepts_supported_boolean():
    values = {
        "x": _value(
            name="x",
            proposed="true",
            status="supported",
        ),
    }

    result = require_resolved(
        values,
        "x",
    )

    assert result == {
        "x": "true",
    }


@pytest.mark.parametrize(
    ("proposed", "status"),
    [
        ("unknown", "supported"),
        ("true", "ambiguous"),
        ("false", "ambiguous"),
        ("true", "unsupported"),
        ("false", "unsupported"),
    ],
)
def test_require_resolved_refuses_uncertain_semantics(
    proposed,
    status,
):
    values = {
        "x": _value(
            name="x",
            proposed=proposed,
            status=status,
        ),
    }

    with pytest.raises(
        UnresolvedScoringState
    ):
        require_resolved(
            values,
            "x",
        )


def test_na_is_not_zero():
    result = na_result(
        "EM1",
        reason="No aplica",
    )

    assert result.applicable is False
    assert result.score is None


@pytest.mark.parametrize(
    "score",
    [0, 1, 2, 3],
)
def test_numeric_scores_are_valid(score):
    result = numeric_result(
        "EM1",
        score,
        reason="test",
    )

    assert result.applicable is True
    assert result.score == score


def test_invalid_numeric_score_rejected():
    with pytest.raises(ValueError):
        numeric_result(
            "EM1",
            4,
            reason="invalido",
        )


def test_result_rejects_zero_as_na():
    with pytest.raises(ValueError):
        EMScoreResult(
            indicator_code="EM1",
            applicable=False,
            score=0,
            reason="incorrecto",
        )


def test_result_rejects_none_for_applicable():
    with pytest.raises(ValueError):
        EMScoreResult(
            indicator_code="EM1",
            applicable=True,
            score=None,
            reason="incorrecto",
        )


def test_dispatcher_returns_na_before_scorer():
    result = score_em_indicator(
        "EM1",
        applicable=False,
        applicability_reason="Sin contenido evaluable",
        values={},
    )

    assert result.applicable is False
    assert result.score is None


def test_dispatcher_rejects_unknown_indicator():
    with pytest.raises(ValueError):
        score_em_indicator(
            "EM14",
            applicable=True,
            applicability_reason="Aplica",
            values={},
        )


def test_unknown_indicator_rejected():
    with pytest.raises(ValueError):
        score_em_indicator(
            "EM99",
            applicable=True,
            applicability_reason="Aplica",
            values={},
        )
