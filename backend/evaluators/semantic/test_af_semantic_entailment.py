"""
EvalIA - Pruebas del validador de sustentación semántica.

Estas pruebas verifican la relación:

    evidencia -> proposición

No evalúan puntuaciones AF ni aplicabilidad de indicadores.

Requieren:
- Ollama en ejecución;
- qwen3.5:9b disponible localmente.
"""

from backend.evaluators.semantic.af_semantic_entailment import (
    validate_semantic_entailment,
)


def _status(evidence: str, proposition: str) -> str:
    result = validate_semantic_entailment(
        evidence=evidence,
        proposition=proposition,
    )
    return result["status"]


def test_supported_explicit_emotion():
    assert _status(
        "Ayer estaba triste",
        "Tristeza",
    ) == "supported"


def test_not_supported_external_event_does_not_prove_emotion():
    assert _status(
        "porque recibí una mala noticia",
        "Malestar emocional por recibir una mala noticia",
    ) == "not_supported"


def test_supported_semantic_paraphrase():
    assert _status(
        "No dejo de pensar en lo que puede salir mal mañana",
        "La persona expresa preocupación por lo que podría ocurrir mañana",
    ) == "supported"


def test_not_supported_indecision_does_not_prove_intention():
    assert _status(
        "No sé si quiero ir mañana",
        "La persona tiene intención de no asistir mañana",
    ) == "not_supported"


def test_not_supported_difficulty_does_not_prove_active_avoidance():
    assert _status(
        "Me cuesta enfrentar esto",
        "La persona está evitando activamente la situación",
    ) == "not_supported"


def test_ambiguous_when_evidence_explicitly_preserves_two_interpretations():
    assert _status(
        "No sé si lo que siento es miedo o simplemente emoción por lo que viene",
        "La persona experimenta miedo",
    ) == "ambiguous"


def test_not_supported_uncertainty_does_not_become_fact():
    assert _status(
        "Tal vez estoy exagerando y puede que ni siquiera esté ansioso",
        "La persona experimenta ansiedad",
    ) == "not_supported"


def test_not_supported_direct_negation():
    assert _status(
        "No estoy triste, en realidad estoy tranquilo",
        "La persona experimenta tristeza",
    ) == "not_supported"