
from backend.evaluators.ce.ce_d.ce4_evidence import (
    validate_ce4_evidence,
)


def test_invented_quote_never_calls_verifier():
    calls = []

    def verifier(*args):
        calls.append(args)
        return "supported"

    extraction = {
        "analysis_complete": True,
        "full_response_audited": True,
        "applicable": True,
        "applicability_evidence": {
            "source": "response",
            "quote": "Primero identifica",
            "interpretation": "La extensi?n requiere estructura visual",
        },
        "rubric_execution": "clear_contextual_verifiable",
        "claims": [
            {
                "source": "response",
                "quote": "Texto que nunca existi?",
                "interpretation": "Supuesto p?rrafo funcional",
            }
        ],
    }

    result = validate_ce4_evidence(
        user_text="Necesito orientaci?n detallada",
        response_text="Primero identifica lo ocurrido.",
        extraction=extraction,
        verify_claim=verifier,
    )

    assert result == {
        "status": "insufficient_evidence",
        "score": None,
    }
    assert calls == []
