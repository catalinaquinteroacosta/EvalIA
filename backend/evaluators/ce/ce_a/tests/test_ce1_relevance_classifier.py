import pytest
from unittest.mock import patch

from backend.evaluators.ce.ce_a import (
    ce1_relevance_classifier as mod,
)


USER = "Necesito ayuda para preparar una entrevista."
RESPONSE = (
    "Practica tus respuestas. "
    "Por cierto, los volcanes son interesantes."
)


def classification(
    *,
    relevance="fully_related",
    deviation=False,
    issues=None,
    complete=True,
):
    return {
        "primary_relevance": relevance,
        "total_deviation": deviation,
        "total_deviation_reason": (
            "La respuesta se evaluo integralmente."
        ),
        "issues": issues if issues is not None else [],
        "analysis_complete": complete,
        "reason": "Relacion contextual examinada.",
    }


def issue(impact="minor"):
    return {
        "description": "Digresion innecesaria.",
        "impact": impact,
        "evidence": (
            "los volcanes son interesantes"
        ),
        "context_justification": (
            "No contribuye a preparar la entrevista."
        ),
    }


def validate(data):
    return mod.validate_classification(
        data,
        user_text=USER,
        response_text=RESPONSE,
    )


def test_full_relevance_without_issues():
    assert validate(
        classification()
    )["analysis_complete"]


@pytest.mark.parametrize(
    "impact",
    ["minor", "major"],
)
def test_documented_impacts(impact):
    result = validate(
        classification(issues=[issue(impact)])
    )
    assert result["issues"][0]["impact"] == impact


def test_total_deviation_requires_unrelated():
    with pytest.raises(ValueError):
        validate(
            classification(
                relevance="fully_related",
                deviation=True,
            )
        )


def test_total_deviation_requires_complete_analysis():
    with pytest.raises(ValueError):
        validate(
            classification(
                relevance="unrelated",
                deviation=True,
                complete=False,
            )
        )


def test_unsupported_evidence_rejected():
    bad = issue()
    bad["evidence"] = "frase inventada"

    with pytest.raises(ValueError):
        validate(
            classification(issues=[bad])
        )


def test_ambiguous_impact_not_complete():
    with pytest.raises(ValueError):
        validate(
            classification(
                issues=[issue("ambiguous")]
            )
        )


def test_semantic_classifier_never_scores():
    with (
        patch.object(
            mod,
            "get_semantic_identity",
            return_value={"model": "test-model"},
        ),
        patch.object(
            mod,
            "run_structured_semantic",
            return_value=classification(
                issues=[issue()]
            ),
        ) as semantic,
        patch.object(mod, "verify_ce1_classification_independently") as second_reader,
    ):
        result = mod.classify_ce1_relevance(
            primary_need="Preparar entrevista",
            primary_coverage="addressed",
            verified_fragments=[{
                "interpretation": (
                    "Contenido ajeno a la entrevista"
                ),
                "evidence": (
                    "los volcanes son interesantes"
                ),
                "verdict": "unnecessary_digression",
            }],
            user_text=USER,
            response_text=RESPONSE,
        )

    assert "score" not in result
    assert result["issues"][0]["impact"] == "minor"
    semantic.assert_called_once()
    second_reader.assert_called_once()


def test_reject_unverified_fragment():
    with pytest.raises(ValueError):
        mod.classify_ce1_relevance(
            primary_need="Preparar entrevista",
            primary_coverage="addressed",
            verified_fragments=[{
                "interpretation": "Contenido ajeno",
                "evidence": "texto inexistente",
                "verdict": "unnecessary_digression",
            }],
            user_text=USER,
            response_text=RESPONSE,
        )
