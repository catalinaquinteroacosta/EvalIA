from backend.evaluators.ir.core.consolidation import consolidate


def base():
    return {
        "family": "IR",
        "indicators": {
            "IR6": {
                "status": "AUDITED",
                "claims": [],
                "missing_components": [],
                "contradictions": [],
                "score": None
            },
            "IR7": {
                "status": "BLOCKED",
                "claims": [],
                "missing_components": [],
                "contradictions": [],
                "score": None
            }
        }
    }


def test_preserves_unresolved_ambiguity():
    rec = {
        "family": "IR",
        "results": {
            "IR6": [{
                "id": "x",
                "verdict": "ambiguous",
                "reason": "No concluyente"
            }]
        }
    }

    result = consolidate(base(), rec)

    assert result["indicators"]["IR6"]["status"] == "BLOCKED"
    assert result["indicators"]["IR6"]["score"] is None


def test_does_not_clear_previous_blocked():
    rec = {
        "family": "IR",
        "results": {
            "IR7": [{
                "id": "x",
                "verdict": "supported",
                "reason": "Lectura semántica"
            }]
        }
    }

    result = consolidate(base(), rec)

    assert result["indicators"]["IR7"]["status"] == "BLOCKED"


def test_preserves_original_findings():
    original = base()
    original["indicators"]["IR6"]["missing_components"] = [
        {"component": "Utilidad"}
    ]

    rec = {
        "family": "IR",
        "results": {
            "IR6": [{
                "id": "x",
                "verdict": "unsupported",
                "reason": "No demostrado"
            }]
        }
    }

    result = consolidate(original, rec)

    assert result["indicators"]["IR6"]["missing_components"] == [
        {"component": "Utilidad"}
    ]

    assert result["indicators"]["IR6"]["score"] is None


def test_no_reconciliation_does_not_create_score():
    result = consolidate(
        base(),
        {"family": "IR", "results": {}}
    )

    assert result["indicators"]["IR6"]["score"] is None


def test_rejects_wrong_family():
    report = base()
    report["family"] = "AF"

    try:
        consolidate(
            report,
            {"family": "IR", "results": {}}
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Debió rechazar otra familia")