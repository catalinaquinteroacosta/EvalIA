from backend.evaluators.pa.verified_evidence_pa import (
    evidence_gate,
)


CONTEXT = {
    "current_user": "Tengo poco tiempo.",
    "current_response": "Haz una lista.",
    "prior_history": [],
}


def test_valid_evidence():
    extraction = {
        "observations": [
            {
                "claim": "Propone una lista",
                "evidence": [
                    {
                        "source": "response",
                        "quote": "Haz una lista.",
                        "history_index": None,
                    }
                ],
            }
        ]
    }

    result = evidence_gate(
        CONTEXT,
        extraction,
        [{"quotes": ["Haz una lista."]}],
    )

    assert result["all_valid"]


def test_invalid_source():
    extraction = {
        "observations": [
            {
                "claim": "Usuario sin tiempo",
                "evidence": [
                    {
                        "source": "response",
                        "quote": "Tengo poco tiempo.",
                        "history_index": None,
                    }
                ],
            }
        ]
    }

    result = evidence_gate(
        CONTEXT,
        extraction,
        [{"quotes": ["Haz una lista."]}],
    )

    assert not result["all_valid"]


def test_invalid_reviewer_quote():
    extraction = {"observations": []}

    result = evidence_gate(
        CONTEXT,
        extraction,
        [{"quotes": ["Tengo poco tiempo."]}],
    )

    assert not result["all_valid"]
