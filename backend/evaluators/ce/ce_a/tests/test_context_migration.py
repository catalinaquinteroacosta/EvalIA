import copy
import pytest

from backend.evaluators.ce.ce_a.extractor import (
    CEAExtractionError,
    validate_extraction,
)
from backend.evaluators.ce.ce_a.tests.test_semantic_contract import (
    USER,
    RESPONSE,
    example,
)


PRIOR = "Tengo una entrevista laboral importante."


def test_accepts_need_from_previous_context():
    data = copy.deepcopy(example())
    data["contextual_needs"] = [{
        "interpretation": "Necesita prepararse.",
        "source": "prior_context",
        "evidence": "Tengo una entrevista laboral importante.",
        "justification": "La entrevista contextualiza la solicitud.",
    }]

    assert validate_extraction(
        data, RESPONSE, USER, PRIOR
    )


def test_accepts_implicit_need_with_real_evidence():
    data = copy.deepcopy(example())
    data["contextual_needs"] = [{
        "interpretation": "Necesita orientaci?n preparatoria.",
        "source": "implicit",
        "evidence": "Tengo una entrevista laboral importante.",
        "justification": "La situaci?n permite inferir la necesidad.",
    }]

    assert validate_extraction(
        data, RESPONSE, USER, PRIOR
    )


def test_rejects_invented_contextual_evidence():
    data = copy.deepcopy(example())
    data["contextual_needs"] = [{
        "interpretation": "Necesita orientaci?n.",
        "source": "prior_context",
        "evidence": "Tengo un examen de medicina.",
        "justification": "Supuestamente lo dijo antes.",
    }]

    with pytest.raises(CEAExtractionError):
        validate_extraction(
            data, RESPONSE, USER, PRIOR
        )
