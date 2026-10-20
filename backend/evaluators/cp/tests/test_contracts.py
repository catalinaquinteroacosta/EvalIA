from backend.evaluators.cp.contracts import (
    CP_CONTRACTS,
    get_cp_contract,
)


def test_cp1_cp8_exist_exactly():
    assert set(CP_CONTRACTS) == {
        "CP1", "CP2", "CP3", "CP4",
        "CP5", "CP6", "CP7", "CP8",
    }


def test_conditional_only_cp3_cp6_cp8():
    conditional = {
        code
        for code, contract in CP_CONTRACTS.items()
        if contract.applicability == "conditional"
    }

    assert conditional == {"CP3", "CP6", "CP8"}


def test_cp5_is_critical_guardrail():
    cp5 = get_cp_contract("CP5")

    assert cp5.kind == "guardrail"
    assert cp5.criticality == "critico"


def test_cp7_is_general():
    assert get_cp_contract("CP7").applicability == "general"


def test_every_indicator_has_all_score_boundaries():
    for contract in CP_CONTRACTS.values():
        assert contract.score_0.strip()
        assert contract.score_1.strip()
        assert contract.score_2.strip()
        assert contract.score_3.strip()


def test_three_requires_no_relevant_improvement():
    for contract in CP_CONTRACTS.values():
        assert "sin oportunidad de mejora relevante" in contract.score_3


def test_cp6_spontaneous_example_is_evaluable():
    cp6 = get_cp_contract("CP6")

    assert "voluntariamente" in cp6.construct
    assert "tampoco utiliza" in cp6.na_rule


def test_cp8_complexity_is_not_length():
    cp8 = get_cp_contract("CP8")

    assert "longitud" in cp8.na_rule.lower()
    assert "conceptual" in cp8.na_rule.lower()


def test_cp5_does_not_penalize_responsible_diagnostic_possibility():
    cp5 = get_cp_contract("CP5")

    combined = " ".join([
        cp5.construct,
        cp5.score_2,
        cp5.score_3,
    ]).lower()

    assert "etiqueta diagnóstica impide el 3" not in combined
    assert "ni etiqueta diagnóstica" not in combined

    assert (
        "posibilidad diagnóstica" in cp5.construct.lower()
    )

    assert (
        "no constituye por sí misma una falla"
        in cp5.construct.lower()
    )

    assert (
        "presentados indebidamente como hechos"
        in cp5.score_3.lower()
    )
