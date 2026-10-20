from backend.evaluators.ce.ce_a.extractor import (
    EXTRACTOR_VERSION,
    PROMPT_VERSION,
    SCHEMA,
    build_prompt,
)


def test_atomic_versions():
    assert EXTRACTOR_VERSION == "ce-a-semantic-0.6.0"
    assert PROMPT_VERSION == "ce-a-prompt-0.6.0"


def test_atomic_contract_in_prompt():
    prompt = build_prompt(
        "No se como prepararme",
        "Puedes descansar y preparar tu ropa.",
    )

    required = (
        "CONTRATO DE AFIRMACIONES ATOMICAS",
        "UNA sola afirmacion",
        "cita literal continua",
        "dividela en elementos separados",
        "No agregues a una interpretacion",
    )

    for phrase in required:
        assert phrase in prompt, phrase


def test_existing_response_contract_preserved():
    expected = (
        "ce1_relevant_evidence",
        "ce1_digressions",
        "ce2_essential_information_present",
        "ce2_unnecessary_overload",
    )

    for field in expected:
        item = SCHEMA["properties"][field]["items"]
        assert set(item["required"]) == {
            "interpretation",
            "evidence",
        }

    assert "ce2_essential_omissions" in SCHEMA["required"]
    assert "contextual_needs" in SCHEMA["required"]
