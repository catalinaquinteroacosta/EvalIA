from backend.evaluators.ir.core import component_engine


def test_verifier_defines_supported_absence():
    prompt = component_engine.VERIFIER_SYSTEM

    assert "present=false + supported" in prompt
    assert "ausencia\nverificada" in prompt


def test_verifier_defines_disagreement():
    prompt = component_engine.VERIFIER_SYSTEM

    assert "present=false + unsupported" in prompt
    assert "desacuerdo" in prompt
