
from backend.evaluators.pa.pa_adversarial_auditor import audit_indicator

def test_pa6_rejection():
    result = audit_indicator(
        None,
        lambda *args: {
            "verdict": "contradicted",
            "reason": "No se justifican alternativas",
            "material_issue": "PA6",
        },
        {"code": "PA6"}, {}, {}, {},
    )
    assert result["verdict"] == "contradicted"

def test_pa8_rejection():
    result = audit_indicator(
        None,
        lambda *args: {
            "verdict": "contradicted",
            "reason": "Solo revisa preocupaciones",
            "material_issue": "PA8",
        },
        {"code": "PA8"}, {}, {}, {},
    )
    assert result["verdict"] == "contradicted"

def test_supported():
    result = audit_indicator(
        None,
        lambda *args: {
            "verdict": "supported",
            "reason": "Evidencia suficiente",
            "material_issue": None,
        },
        {"code": "PA8"}, {}, {}, {},
    )
    assert result["verdict"] == "supported"

def test_other_indicator_no_api():
    def forbidden(*args):
        raise AssertionError("No debe llamar API")
    assert audit_indicator(
        None, forbidden, {"code": "PA4"}, {}, {}, {}
    ) is None

def test_invalid_verdict():
    import pytest
    with pytest.raises(ValueError):
        audit_indicator(
            None,
            lambda *args: {
                "verdict": "approved",
                "reason": "Invalido",
            },
            {"code": "PA6"}, {}, {}, {},
        )
