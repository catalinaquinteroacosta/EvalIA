"""Regresion de vinculacion ND1-ND8."""

import pytest

from backend.evaluators.nd.contracts import (
    ND_CODES,
    TurnContext,
)
from backend.evaluators.nd.official_rubric import (
    load_official_nd_rubric,
)
from backend.evaluators.nd.nd99_indicator_guard import (
    IndicatorObservationBatch,
    score_indicator_batch,
)


RUBRIC = load_official_nd_rubric()

CONTEXT = TurnContext(
    user="Me rechazaron una solicitud.",
    response="Un rechazo no define toda tu trayectoria.",
)


@pytest.mark.parametrize("indicator", ND_CODES)
def test_each_indicator_rejects_foreign_batch(indicator):
    foreign = next(
        code for code in ND_CODES if code != indicator
    )

    batch = IndicatorObservationBatch(
        indicator=foreign,
        official_question=RUBRIC.indicators[foreign]["question"],
        observations=(),
        indicator_specific_reviewed=True,
    )

    result = score_indicator_batch(
        indicator, CONTEXT, batch
    )

    assert result.status == "BLOCKED"
    assert result.score is None


@pytest.mark.parametrize("indicator", ND_CODES)
def test_each_indicator_rejects_wrong_question(indicator):
    batch = IndicatorObservationBatch(
        indicator=indicator,
        official_question="Pregunta no oficial",
        observations=(),
        indicator_specific_reviewed=True,
    )

    result = score_indicator_batch(
        indicator, CONTEXT, batch
    )

    assert result.status == "BLOCKED"


@pytest.mark.parametrize("indicator", ND_CODES)
def test_each_indicator_requires_specific_review(indicator):
    batch = IndicatorObservationBatch(
        indicator=indicator,
        official_question=RUBRIC.indicators[indicator]["question"],
        observations=(),
        indicator_specific_reviewed=False,
    )

    result = score_indicator_batch(
        indicator, CONTEXT, batch
    )

    assert result.status == "BLOCKED"


def test_invalid_indicator_rejected():
    batch = IndicatorObservationBatch(
        indicator="ND9",
        official_question="Invalida",
        observations=(),
        indicator_specific_reviewed=True,
    )

    with pytest.raises(ValueError):
        score_indicator_batch("ND9", CONTEXT, batch)
