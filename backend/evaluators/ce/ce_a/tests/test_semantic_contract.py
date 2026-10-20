import copy

import pytest

from backend.evaluators.ce.ce_a import extractor


USER = (
    "Ma?ana tengo una entrevista. "
    "?Qu? puedo hacer esta noche?"
)

RESPONSE = (
    "Puedes preparar tu ropa y los documentos "
    "que necesites para ma?ana."
)


def example():
    return {
        "primary_need": (
            "Prepararse para una entrevista"
        ),
        "explicit_needs": [
            {
                "interpretation": (
                    "Solicita consejos para esta noche"
                ),
                "user_evidence": (
                    "?Qu? puedo hacer esta noche?"
                ),
            }
        ],
        "contextual_needs": [],
        "ce1_relevant_evidence": [
            {
                "interpretation": (
                    "Recomienda preparar anticipadamente "
                    "los elementos necesarios"
                ),
                "evidence": (
                    "Puedes preparar tu ropa y los documentos"
                ),
            }
        ],
        "ce1_digressions": [],
        "ce2_essential_information_present": [
            {
                "interpretation": (
                    "Propone una acci?n preparatoria"
                ),
                "evidence": (
                    "preparar tu ropa y los documentos"
                ),
            }
        ],
        "ce2_essential_omissions": [],
        "ce2_unnecessary_overload": [],
    }


def test_accepts_valid_paraphrase():
    assert extractor.validate_extraction(
        example(), RESPONSE, USER
    )


def test_rejects_invented_evidence():
    result = example()
    result["ce1_relevant_evidence"][0][
        "evidence"
    ] = "Debes preparar todo anticipadamente."

    with pytest.raises(
        extractor.CEAExtractionError
    ):
        extractor.validate_extraction(
            result, RESPONSE, USER
        )


def test_rejects_empty_interpretation():
    result = example()
    result["ce1_relevant_evidence"][0][
        "interpretation"
    ] = ""

    with pytest.raises(
        extractor.CEAExtractionError
    ):
        extractor.validate_extraction(
            result, RESPONSE, USER
        )


def test_rejects_invented_user_need():
    result = example()
    result["explicit_needs"][0][
        "user_evidence"
    ] = "Necesito consejos para dormir."

    with pytest.raises(
        extractor.CEAExtractionError
    ):
        extractor.validate_extraction(
            result, RESPONSE, USER
        )


def test_omission_requires_user_evidence():
    result = example()
    result["ce2_essential_omissions"] = [
        {
            "missing_information": (
                "Consejos para dormir"
            ),
            "context_justification": (
                "El usuario lo solicit?"
            ),
            "source": "current_user",
            "user_evidence": (
                "Necesito consejos para dormir"
            ),
        }
    ]

    with pytest.raises(
        extractor.CEAExtractionError
    ):
        extractor.validate_extraction(
            result, RESPONSE, USER
        )


def test_rejects_extra_score():
    result = example()
    result["score"] = 3

    with pytest.raises(
        extractor.CEAExtractionError
    ):
        extractor.validate_extraction(
            result, RESPONSE, USER
        )


def test_openai_mock(monkeypatch):
    calls = []

    def fake_provider(**kwargs):
        calls.append(kwargs)
        return copy.deepcopy(example())

    monkeypatch.setattr(
        extractor,
        "run_structured_semantic",
        fake_provider,
    )

    result = extractor.extract_ce_a(
        USER,
        RESPONSE,
        use_cache=False,
    )

    assert result["ce1_relevant_evidence"]
    assert calls[0]["provider"] == "openai"


def test_prompt_preserves_semantics():
    prompt = extractor.build_prompt(
        USER, RESPONSE
    )

    assert "Parafrasear correctamente es v?lido" in prompt
    assert "Inventar evidencia no lo es" in prompt
    assert "No asignes puntuaciones" in prompt
