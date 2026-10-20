import pytest

from backend.evaluators.ir.core.contracts import Context
from backend.evaluators.ir.core.semantic import INDICATORS
from backend.evaluators.ir.audit_runner import audit_saved


def make_saved():
    return {
        "family": "IR",
        "indicators": {
            k: {
                "claims": [{
                    "claim": "Componente",
                    "verification": "supported"
                }]
            }
            for k in INDICATORS
        }
    }


def fake_audit(ctx, indicator):
    return {
        "indicator": indicator,
        "supported_components": [],
        "missing_components": (
            [{
                "component": "Utilidad",
                "reason": "No demostrada"
            }]
            if indicator == "IR6" else []
        ),
        "contradictions": [],
    }


def test_all_eight_audited():
    result = audit_saved(
        Context("Usuario", "Respuesta"),
        make_saved(),
        auditor=fake_audit,
    )

    assert len(result["indicators"]) == 8
    assert all(
        x["score"] is None
        for x in result["indicators"].values()
    )


def test_ir6_missing_component_preserved():
    result = audit_saved(
        Context("Usuario", "Respuesta"),
        make_saved(),
        auditor=fake_audit,
    )

    assert len(
        result["indicators"]["IR6"]["missing_components"]
    ) == 1


def test_missing_indicator_rejected():
    saved = make_saved()
    del saved["indicators"]["IR4"]

    with pytest.raises(ValueError):
        audit_saved(
            Context("Usuario", "Respuesta"),
            saved,
            auditor=fake_audit,
        )


def test_contradiction_blocks_only_affected_indicator():
    def auditor(ctx, indicator):
        result = fake_audit(ctx, indicator)
        if indicator == "IR3":
            result["contradictions"] = [{
                "component": "Contradicción",
                "reason": "Contradicción demostrada",
            }]
        return result

    result = audit_saved(
        Context("Usuario", "Respuesta"),
        make_saved(),
        auditor=auditor,
    )

    assert result["indicators"]["IR3"]["status"] == "BLOCKED"
    assert result["indicators"]["IR2"]["status"] == "AUDITED"


def test_wrong_family_rejected():
    saved = make_saved()
    saved["family"] = "AF"

    with pytest.raises(ValueError):
        audit_saved(
            Context("Usuario", "Respuesta"),
            saved,
            auditor=fake_audit,
        )