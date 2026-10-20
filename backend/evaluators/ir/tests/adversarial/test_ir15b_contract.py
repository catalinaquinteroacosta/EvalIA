from backend.evaluators.ir.core import component_engine


def test_ir6_extractor_distinguishes_reformulation():
    prompt = component_engine.EXTRACTOR_SYSTEM

    assert (
        "No basta con que el usuario mencione ansiedad"
        in prompt
    )
    assert (
        "Evalua los dos componentes independientemente."
        in prompt
    )


def test_ir6_verifier_checks_extractor_claim():
    prompt = component_engine.VERIFIER_SYSTEM

    assert "Si present=false:" in prompt
    assert "supported = ausencia respaldada." in prompt
    assert (
        "No confundas ausencia del componente con"
        in prompt
    )


def test_ir6_verifier_has_negative_boundary():
    prompt = component_engine.VERIFIER_SYSTEM

    assert "EJEMPLO NEGATIVO:" in prompt
    assert "EJEMPLO POSITIVO:" in prompt
