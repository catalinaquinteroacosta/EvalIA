"""Pruebas de ausencia explicita ND99."""

from backend.evaluators.nd.nd99_absence_contract import (
    AbsenceFinding,
    reconcile_with_absence,
)
from backend.evaluators.nd.nd99_polarity_contract import (
    PolarityFinding,
)


RESPONSE = "Un rechazo no define toda tu trayectoria."
NAME = "reinforces_negative_idea"


def polarity(verdict):
    return PolarityFinding(
        fact_name=NAME,
        verdict=verdict,
        quote=RESPONSE,
        reason="Analisis de la afirmacion exacta",
        complete_response_examined=True,
    )


def absence(value):
    return AbsenceFinding(
        fact_name=NAME,
        explicitly_absent=value,
        reason="Revision explicita de toda la respuesta",
        complete_response_examined=True,
    )


def test_confirmed_absence():
    result = reconcile_with_absence(
        NAME,
        polarity("not_supported"),
        polarity("not_supported"),
        absence(True),
        absence(True),
        RESPONSE,
    )
    assert result.extraction_value == "absent"


def test_missing_absence_blocks():
    result = reconcile_with_absence(
        NAME,
        polarity("not_supported"),
        polarity("not_supported"),
        None,
        None,
        RESPONSE,
    )
    assert result.extraction_value == "uncertain"


def test_absence_disagreement_blocks():
    result = reconcile_with_absence(
        NAME,
        polarity("not_supported"),
        polarity("not_supported"),
        absence(True),
        absence(False),
        RESPONSE,
    )
    assert result.extraction_value == "uncertain"


def test_supported_presence_preserved():
    result = reconcile_with_absence(
        NAME,
        polarity("supported"),
        polarity("supported"),
        absence(True),
        absence(True),
        RESPONSE,
    )
    assert result.extraction_value == "present"


def test_ambiguous_polarity_blocks():
    result = reconcile_with_absence(
        NAME,
        polarity("ambiguous"),
        polarity("ambiguous"),
        absence(True),
        absence(True),
        RESPONSE,
    )
    assert result.extraction_value == "uncertain"
