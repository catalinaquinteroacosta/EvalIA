import pytest

from backend.evaluators.ce.ce_a.claim_verifier import (
    CEAClaimError,
    aggregate_claims,
    validate_decomposition,
)


def decomposition(complete=True):
    return {
        "claims": [
            "The response validates anxiety.",
            "The response reduces perfection pressure.",
        ],
        "decomposition_complete": complete,
        "reason": "Two independent assertions.",
    }


def checks(first="supported", second="supported"):
    return [
        {
            "claim": "The response validates anxiety.",
            "verdict": first,
        },
        {
            "claim": "The response reduces perfection pressure.",
            "verdict": second,
        },
    ]


def test_all_supported():
    result = aggregate_claims(decomposition(), checks())
    assert result["verdict"] == "supported"


def test_partial_support_rejected():
    result = aggregate_claims(
        decomposition(),
        checks("supported", "not_supported"),
    )
    assert result["verdict"] == "not_supported"


def test_uncertain_claim_blocks_acceptance():
    result = aggregate_claims(
        decomposition(),
        checks("supported", "ambiguous"),
    )
    assert result["verdict"] == "ambiguous"


def test_incomplete_decomposition_blocks_acceptance():
    result = aggregate_claims(
        decomposition(False),
        checks(),
    )
    assert result["verdict"] == "ambiguous"


def test_missing_claim_verification_fails():
    with pytest.raises(CEAClaimError):
        aggregate_claims(decomposition(), checks()[:1])


def test_wrong_claim_mapping_fails():
    items = checks()
    items[1]["claim"] = "A different assertion."
    with pytest.raises(CEAClaimError):
        aggregate_claims(decomposition(), items)


def test_empty_claims_rejected():
    item = decomposition()
    item["claims"] = []
    with pytest.raises(CEAClaimError):
        validate_decomposition(item)


def test_duplicate_claims_rejected():
    item = decomposition()
    item["claims"][1] = item["claims"][0]
    with pytest.raises(CEAClaimError):
        validate_decomposition(item)
