import copy

import pytest

from backend.evaluators.ce.ce_a import extractor
from backend.evaluators.ce.ce_a import citation_repair
from backend.evaluators.ce.ce_a.tests.test_semantic_contract import (
    USER,
    RESPONSE,
    example,
)


def broken_result():
    result = copy.deepcopy(example())
    result["ce1_relevant_evidence"][0]["evidence"] = (
        "Una cita inventada."
    )
    return result


def test_valid_extraction_does_not_call_repair(monkeypatch):
    monkeypatch.setattr(
        extractor,
        "run_structured_semantic",
        lambda **kwargs: copy.deepcopy(example()),
    )

    def unexpected_repair(*args, **kwargs):
        raise AssertionError(
            "No debe reparar una extracci?n v?lida."
        )

    monkeypatch.setattr(
        citation_repair,
        "repair_citations",
        unexpected_repair,
    )

    result = extractor.extract_ce_a(
        USER,
        RESPONSE,
        use_cache=False,
    )

    assert result == example()


def test_invalid_quote_triggers_one_repair(monkeypatch):
    calls = []

    monkeypatch.setattr(
        extractor,
        "run_structured_semantic",
        lambda **kwargs: broken_result(),
    )

    def fake_repair(raw, **kwargs):
        calls.append(raw)
        return copy.deepcopy(example())

    monkeypatch.setattr(
        citation_repair,
        "repair_citations",
        fake_repair,
    )

    result = extractor.extract_ce_a(
        USER,
        RESPONSE,
        use_cache=False,
    )

    assert result == example()
    assert len(calls) == 1


def test_failed_repair_stops_execution(monkeypatch):
    calls = []

    monkeypatch.setattr(
        extractor,
        "run_structured_semantic",
        lambda **kwargs: broken_result(),
    )

    def fake_repair(raw, **kwargs):
        calls.append(raw)
        return broken_result()

    monkeypatch.setattr(
        citation_repair,
        "repair_citations",
        fake_repair,
    )

    with pytest.raises(extractor.CEAExtractionError):
        extractor.extract_ce_a(
            USER,
            RESPONSE,
            use_cache=False,
        )

    assert len(calls) == 1
