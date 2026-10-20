import pytest

from backend.evaluators.cp.context import PriorTurn
from backend.evaluators.cp.extractor import (
    SOURCE_VALUES,
    _validate_exact_quote,
    build_cp_family_prompt,
)


def history():
    return (
        PriorTurn(
            role="user",
            text="USER PRIOR FACT",
        ),
        PriorTurn(
            role="assistant",
            text="ASSISTANT PRIOR CLAIM",
        ),
    )


def test_history_source_enabled():
    assert SOURCE_VALUES == [
        "history",
        "user",
        "response",
    ]


def test_prompt_has_temporal_sources():
    prompt = build_cp_family_prompt(
        prior_history=history(),
        user_text="CURRENT USER FACT",
        response_text="CURRENT RESPONSE FACT",
    )

    assert "PRIOR_HISTORY" in prompt
    assert "CURRENT_USER" in prompt
    assert "CURRENT_RESPONSE" in prompt
    assert "Future turns are forbidden." in prompt
    assert "[HISTORY_INDEX=0 | ROLE=user]" in prompt
    assert "[HISTORY_INDEX=1 | ROLE=assistant]" in prompt


def test_history_exact_index_valid():
    _validate_exact_quote(
        source="history",
        history_index=0,
        quote="USER PRIOR FACT",
        user_text="CURRENT USER FACT",
        response_text="CURRENT RESPONSE FACT",
        prior_history=history(),
    )


def test_history_wrong_index_rejected():
    with pytest.raises(ValueError):
        _validate_exact_quote(
            source="history",
            history_index=1,
            quote="USER PRIOR FACT",
            user_text="CURRENT USER FACT",
            response_text="CURRENT RESPONSE FACT",
            prior_history=history(),
        )


def test_history_without_index_rejected():
    with pytest.raises(ValueError):
        _validate_exact_quote(
            source="history",
            history_index=None,
            quote="USER PRIOR FACT",
            user_text="CURRENT USER FACT",
            response_text="CURRENT RESPONSE FACT",
            prior_history=history(),
        )


def test_user_with_history_index_rejected():
    with pytest.raises(ValueError):
        _validate_exact_quote(
            source="user",
            history_index=0,
            quote="CURRENT USER FACT",
            user_text="CURRENT USER FACT",
            response_text="CURRENT RESPONSE FACT",
            prior_history=history(),
        )


def test_response_with_history_index_rejected():
    with pytest.raises(ValueError):
        _validate_exact_quote(
            source="response",
            history_index=0,
            quote="CURRENT RESPONSE FACT",
            user_text="CURRENT USER FACT",
            response_text="CURRENT RESPONSE FACT",
            prior_history=history(),
        )


def test_history_cannot_masquerade_as_current_user():
    with pytest.raises(ValueError):
        _validate_exact_quote(
            source="user",
            history_index=None,
            quote="USER PRIOR FACT",
            user_text="CURRENT USER FACT",
            response_text="CURRENT RESPONSE FACT",
            prior_history=history(),
        )


def test_empty_history_explicit():
    prompt = build_cp_family_prompt(
        prior_history=(),
        user_text="CURRENT USER",
        response_text="CURRENT RESPONSE",
    )

    assert "[NO PRIOR HISTORY]" in prompt
