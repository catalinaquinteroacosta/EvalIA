from copy import deepcopy

import pytest

from backend.evaluators.ce.ce_a.omission_resolution import (
    OmissionResolutionError,
    resolve_omissions,
)


OMISSION = {
    "missing_information": "Falta un horario.",
    "context_justification": "Podria ayudar.",
    "user_evidence": "Que hago esta noche?",
    "source": "current_user",
}


def check(verdict, index=0):
    return {
        "index": index,
        **deepcopy(OMISSION),
        "verdict": verdict,
        "reason": "Independent verification.",
    }


def test_rejected_omission_is_logged_not_scored():
    original = {
        "ce2_essential_omissions": [deepcopy(OMISSION)]
    }
    snapshot = deepcopy(original)
    result = resolve_omissions(
        original, [check("not_supported")]
    )
    assert original == snapshot
    assert result["resolved_extraction"][
        "ce2_essential_omissions"
    ] == []
    assert result["resolution_log"][0]["action"] == (
        "excluded_after_verification"
    )
    assert result["scoring_authorized"] is False


def test_supported_omission_is_retained():
    result = resolve_omissions(
        {"ce2_essential_omissions": [deepcopy(OMISSION)]},
        [check("supported")],
    )
    assert result["resolved_extraction"][
        "ce2_essential_omissions"
    ] == [OMISSION]


def test_no_omissions_requires_no_checks():
    result = resolve_omissions(
        {"ce2_essential_omissions": []},
        [],
    )
    assert result["resolution_log"] == []


@pytest.mark.parametrize(
    "checks",
    [
        [],
        [check("ambiguous")],
        [check("invalid")],
        [check("supported", index=1)],
        [check("supported"), check("supported")],
        [{**check("supported"), "user_evidence": "Wrong"}],
        [{**check("supported"), "index": True}],
    ],
)
def test_invalid_or_incomplete_verification_blocks(checks):
    with pytest.raises(OmissionResolutionError):
        resolve_omissions(
            {"ce2_essential_omissions": [deepcopy(OMISSION)]},
            checks,
        )
