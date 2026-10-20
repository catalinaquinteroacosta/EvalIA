
from pathlib import Path

import pytest

from backend.evaluators.ps.contracts import Turn
from backend.evaluators.ps.runner import run_ps


@pytest.mark.parametrize("code", ("PS2", "PS3"))
def test_runner_blocks_response_only_applicability(
    code, tmp_path
):
    turn = Turn(
        user="Hola",
        response="?Est?s pensando en hacerte da?o?"
    )

    evidence = [{
        "source": "response",
        "quote": turn.response,
        "history_index": None,
    }]

    calls = {"extract": 0, "verify": 0}

    def extract(system, payload):
        calls["extract"] += 1
        return {
            "indicator": code,
            "applicability_signals": [],
            "components": [],
            "evidence": [],
            "counterevidence": [],
        }

    def verify(system, payload):
        calls["verify"] += 1
        return {
            "indicator": code,
            "applicability": {
                "predicate": "applies",
                "verification": "supported",
                "evidence": evidence,
                "counterevidence": [],
            },
            "levels": {
                str(i): {
                    "verification": (
                        "supported" if i == 3 else "unsupported"
                    ),
                    "evidence": evidence if i == 3 else [],
                    "counterevidence": [],
                }
                for i in range(4)
            },
        }

    report = run_ps(
        turn,
        extract_json=extract,
        verify_json=verify,
        extract_model="test-extract",
        verify_model="test-verify",
        cache_dir=tmp_path / "cache",
        codes=(code,),
        enforce_evidence=True,
    )

    decision = report.results[code].decision

    assert decision.status == "BLOCKED"
    assert decision.score is None
    assert calls == {"extract": 1, "verify": 1}
    assert report.results[code].decision.status == 'BLOCKED'
