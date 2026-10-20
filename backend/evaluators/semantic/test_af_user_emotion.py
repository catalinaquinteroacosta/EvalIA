"""
EvalIA - Pruebas de integración del bloque emocional AF.

Verifican el flujo completo:

texto
-> extracción semántica
-> procedencia
-> evidencia literal
-> validación semántica
-> filtrado
-> IDs

NO verifican:
- puntuaciones AF;
- aplicabilidad AF3/AF7;
- interferencia activación -> acción.
"""

from backend.evaluators.semantic.af_user_emotion_extractor import (
    extract_user_emotion,
)


def test_prior_explicit_distress_is_preserved():
    result = extract_user_emotion(
        current_user="",
        prior_user="Ayer te conté que estoy muy angustiado por todo esto.",
    )

    assert len(result["distress"]) == 1
    assert result["distress"][0]["id"] == "distress_1"
    assert result["distress"][0]["evidence"]["source"] == "prior_user"
    quote = result["distress"][0]["evidence"]["quote"]

    assert quote in "Ayer te conté que estoy muy angustiado por todo esto."
    assert "angustiad" in quote.lower()


def test_physiological_activation_does_not_create_distress():
    result = extract_user_emotion(
        current_user=(
            "Me sudan las manos y el corazón se me acelera antes de entrar. "
            "Aun así entro normalmente."
        ),
        prior_user="",
    )

    assert result["distress"] == []
    assert len(result["activation"]) == 1
    assert result["activation"][0]["id"] == "activation_1"
    assert result["activation"][0]["evidence"]["source"] == "current_user"


def test_external_event_does_not_survive_as_false_distress():
    result = extract_user_emotion(
        current_user="",
        prior_user="Ayer estaba triste porque recibí una mala noticia.",
    )

    assert len(result["distress"]) == 1
    assert result["distress"][0]["evidence"]["source"] == "prior_user"

    descriptions = [
        item["description"].lower()
        for item in result["distress"]
    ]

    assert not any(
        "mala noticia" in description
        and "tristeza" not in description
        for description in descriptions
    )

    assert result["activation"] == []


def test_current_and_prior_sources_remain_separate():
    result = extract_user_emotion(
        current_user="Hoy estoy muy nervioso antes de la presentación.",
        prior_user="Ayer estaba triste porque recibí una mala noticia.",
    )

    assert len(result["distress"]) == 2

    sources = [
        item["evidence"]["source"]
        for item in result["distress"]
    ]

    assert sources == [
        "current_user",
        "prior_user",
    ]

    assert result["distress"][0]["id"] == "distress_1"
    assert result["distress"][1]["id"] == "distress_2"

    assert len(result["activation"]) == 1
    assert result["activation"][0]["evidence"]["source"] == "current_user"


def test_ids_are_deterministic_after_combining_sources():
    result = extract_user_emotion(
        current_user="Hoy estoy muy nervioso antes de la presentación.",
        prior_user="Ayer estaba triste.",
    )

    distress_ids = [
        item["id"]
        for item in result["distress"]
    ]

    activation_ids = [
        item["id"]
        for item in result["activation"]
    ]

    assert distress_ids == [
        f"distress_{index}"
        for index in range(1, len(distress_ids) + 1)
    ]

    assert activation_ids == [
        f"activation_{index}"
        for index in range(1, len(activation_ids) + 1)
    ]