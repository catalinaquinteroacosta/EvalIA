
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
REVIEW = ROOT / "reports" / "ps23_final_review"

def load(name):
    return json.loads(
        (REVIEW / name).read_text(encoding="utf-8-sig")
    )

def decision_for(case_id, indicator):
    decisions = load("ps23_audit_decisions.json")["decisions"]
    matches = [
        x for x in decisions
        if x["case_id"] == case_id
        and x["indicator"] == indicator
    ]
    assert len(matches) == 1
    return matches[0]

def test_greeting_ps3_not_finalized():
    decision = decision_for("greeting", "PS3")
    assert decision["audit_status"] == "CANDIDATE_NA"
    assert decision["audit_status"] != "SCORED"

def test_urgent_ps2_remains_blocked():
    decision = decision_for("urgent", "PS2")
    assert decision["audit_status"] == "BLOCKED"

def test_urgent_ps2_ambiguity_preserved():
    audit = load("ps23_semantic_audit.json")
    case = next(
        x for x in audit["cases"]
        if x["indicator"] == "PS2"
    )
    assert case["verification"]["unresolved_ambiguity"]

def test_urgent_ps3_remains_blocked():
    decision = decision_for("urgent", "PS3")
    assert decision["audit_status"] == "BLOCKED"
    assert decision["previous_score_validated"] is False

def test_urgent_ps3_conflicting_levels():
    audit = load("ps23_semantic_audit.json")
    case = next(
        x for x in audit["cases"]
        if x["indicator"] == "PS3"
    )
    verification = case["normalized_verification"]
    assert verification["level_2_supported"] is True
    assert verification["level_3_supported"] is True

def test_no_historical_score_changes():
    report = load("ps23_audit_decisions.json")
    assert report["historical_scores_modified"] is False
    assert report["rubric_modified"] is False

def test_exactly_three_audited_cases():
    report = load("ps23_audit_decisions.json")
    assert len(report["decisions"]) == 3
