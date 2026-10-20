from copy import deepcopy

import pytest

from backend.evaluators.ce.ce_a.ce1_unaddressed_need import (
    CE1UnaddressedNeedError,
    validate_unaddressed_need,
)

USER = "Necesito saber como prepararme esta noche."
PRIOR = "Manana tengo una entrevista laboral."


def sample():
    return {
        "need": "Orientacion para prepararse esta noche.",
        "source": "current_user",
        "evidence": "como prepararme esta noche",
        "explanation": (
            "La respuesta no aborda esta solicitud."
        ),
    }


def check(item):
    return validate_unaddressed_need(
        item,
        user_text=USER,
        prior_context=PRIOR,
    )


def test_valid_current_user_evidence():
    item = sample()
    original = deepcopy(item)
    assert check(item) == original
    assert item == original


def test_valid_prior_context_evidence():
    item = sample()
    item["source"] = "prior_context"
    item["evidence"] = "entrevista laboral"
    assert check(item) == item


@pytest.mark.parametrize(
    "field,value",
    [
        ("need", ""),
        ("source", "unknown"),
        ("evidence", "cita inventada"),
        ("explanation", ""),
    ],
)
def test_invalid_fields(field, value):
    item = sample()
    item[field] = value

    with pytest.raises(CE1UnaddressedNeedError):
        check(item)


def test_wrong_evidence_source():
    item = sample()
    item["source"] = "prior_context"

    with pytest.raises(CE1UnaddressedNeedError):
        check(item)


def test_additional_fields_rejected():
    item = sample()
    item["score"] = 0

    with pytest.raises(CE1UnaddressedNeedError):
        check(item)
