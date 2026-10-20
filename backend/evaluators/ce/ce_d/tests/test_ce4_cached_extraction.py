
import pytest

from backend.evaluators.ce.ce_d.ce4_cached_extraction import (
    CE4ExtractionError,
    extract_ce4_cached,
    validate_extraction,
)


VALID = {
    "analysis_complete": True,
    "full_response_audited": True,
    "applicable": True,
    "applicability_evidence": {
        "source": "response",
        "quote": "Primero",
        "interpretation": "Necesita estructura",
    },
    "claims": [{
        "source": "response",
        "quote": "Segundo",
        "interpretation": "Organizacion funcional",
    }],
    "rubric_execution": "adequate_limited",
}


def test_valid_extraction():
    assert validate_extraction(VALID) == VALID


def test_invalid_extraction_rejected():
    invalid = dict(VALID)
    invalid["applicable"] = "yes"

    with pytest.raises(CE4ExtractionError):
        validate_extraction(invalid)


def test_cache_hit_revalidated():
    def cache_operation(**kwargs):
        return {"invalid": True}

    with pytest.raises(CE4ExtractionError):
        extract_ce4_cached(
            user_text="Ayuda",
            response_text="Primero. Segundo.",
            cache_operation=cache_operation,
        )


def test_cache_hit_does_not_call_provider():
    def runner(**kwargs):
        raise AssertionError("API no autorizada")

    def cache_operation(**kwargs):
        return dict(VALID)

    result = extract_ce4_cached(
        user_text="Ayuda",
        response_text="Primero. Segundo.",
        runner=runner,
        cache_operation=cache_operation,
    )

    assert result == VALID


def test_cache_identity_includes_context():
    captured = []

    def cache_operation(**kwargs):
        captured.append(kwargs["inputs"])
        return dict(VALID)

    for context in ("", "Contexto anterior"):
        extract_ce4_cached(
            user_text="Ayuda",
            response_text="Primero. Segundo.",
            prior_context=context,
            cache_operation=cache_operation,
        )

    assert captured[0] != captured[1]
