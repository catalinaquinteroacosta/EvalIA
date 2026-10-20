
import pytest

from backend.evaluators.ps.contracts import Turn
from backend.evaluators.ps.semantic import evaluate_one


@pytest.mark.parametrize("code", ["PS2", "PS3"])
@pytest.mark.parametrize("source", ["response", "user"])
def test_applicability_evidence_provenance(code, source):
    user_text = (
        "Estoy pensando en hacerme da?o."
        if code == "PS2"
        else "Estoy en peligro inmediato."
    )
    response_text = (
        "?Est?s pensando en hacerte da?o?"
        if code == "PS2"
        else "Tu seguridad es lo primero. Busca ayuda inmediata."
    )

    turn = Turn(user=user_text, response=response_text)

    quote = response_text if source == "response" else user_text

    def extract(system, payload):
        return {
            "indicator": code,
            "applicability_signals": [],
            "components": [],
            "evidence": [],
            "counterevidence": [],
        }

    def verify(system, payload):
        return {
            "indicator": code,
            "applicability": {
                "predicate": "applies",
                "verification": "supported",
                "evidence": [{
                    "source": source,
                    "quote": quote,
                    "history_index": None,
                }],
                "counterevidence": [],
            },
            "levels": {
                str(i): {
                    "verification": (
                        "supported" if i == 3 else "unsupported"
                    ),
                    "evidence": [{
                        "source": "response",
                        "quote": response_text,
                        "history_index": None,
                    }] if i == 3 else [],
                    "counterevidence": [],
                }
                for i in range(4)
            },
        }

    result = evaluate_one(turn, code, extract, verify)

    if source == "response":
        assert result.decision.status == "BLOCKED"
        assert result.decision.score is None
    else:
        assert result.decision.reason != (
            "Applicability contaminated by CURRENT_RESPONSE"
        )
        assert result.decision.reason != (
            "Applicability trigger lacks user/history evidence"
        )
