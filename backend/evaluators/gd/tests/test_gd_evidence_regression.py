import json
from pathlib import Path

from backend.evaluators.gd.gd_schemas import GDContext
from backend.evaluators.gd.gd_level_semantic import (
    resolve_verified_levels,
)


def _real_pilot():
    folder = Path("backend/evaluators/gd/reports")
    reports = sorted(
        (
            p for p in folder.glob("GD_REAL_01_*.json")
            if "ERROR" not in p.name
        ),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not reports:
        raise AssertionError("Falta piloto GD real.")

    data = json.loads(
        reports[0].read_text(encoding="utf-8-sig")
    )

    return data


def _resolve(data):
    return resolve_verified_levels(
        GDContext(**data["context"]),
        data["classification"],
        data["level_verification"],
        applicability=data["applicability"],
    )


def test_positive_evidence_is_preserved():
    data = _real_pilot()
    results = _resolve(data)

    for code in ("GD1", "GD3", "GD4", "GD5", "GD8"):
        result = results[code]

        assert result.status == "SCORED"
        assert result.score == 3
        assert result.evidence

        for evidence in result.evidence:
            assert evidence.source == "CURRENT_RESPONSE"
            assert evidence.quote in data["context"]["current_response"]


def test_guardrail_absence_does_not_require_positive_quote():
    data = _real_pilot()
    results = _resolve(data)

    for code in ("GD2", "GD6", "GD7"):
        result = results[code]
        assert result.status == "SCORED"
        assert result.score == 3


def test_unverified_level_is_blocked():
    data = _real_pilot()

    verification = json.loads(
        json.dumps(data["level_verification"])
    )

    for item in verification["verdicts"]:
        if item["code"] == "GD1":
            item["verdict"] = "ambiguous"

    results = resolve_verified_levels(
        GDContext(**data["context"]),
        data["classification"],
        verification,
        applicability=data["applicability"],
    )

    assert results["GD1"].status == "BLOCKED"
    assert results["GD1"].score is None


def test_conditional_na_has_no_score():
    data = _real_pilot()

    applicability = dict(data["applicability"])
    applicability["GD5"] = "NA"

    results = resolve_verified_levels(
        GDContext(**data["context"]),
        data["classification"],
        data["level_verification"],
        applicability=applicability,
    )

    assert results["GD5"].status == "NA"
    assert results["GD5"].score is None
