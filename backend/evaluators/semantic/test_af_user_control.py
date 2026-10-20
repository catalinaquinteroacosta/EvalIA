"""
EvalIA — Tests deterministas del bloque de Controlabilidad.

Estos tests NO consultan Qwen/Ollama.

Validan:
- aceptación de evidencia literal válida;
- rechazo de evidencia inventada;
- rechazo de fuentes no permitidas;
- estructura básica de las tres categorías;
- comportamiento con listas vacías.

Las pruebas semánticas del modelo local se mantienen separadas
porque dependen de inferencia LLM.
"""

from __future__ import annotations

import pytest

from backend.evaluators.semantic.af_user_control_extractor import (
    AFUserControlExtractorError,
    _verify_control_evidence,
)


def test_control_accepts_valid_current_user_evidence():
    result = {
        "modifiable_components": [
            {
                "id": "modifiable_1",
                "description": "Escribir al profesor.",
                "evidence": {
                    "quote": "puedo escribirle al profesor",
                    "source": "current_user",
                },
            }
        ],
        "unmodifiable_now": [],
        "uncertain_outcomes": [],
    }

    verified = _verify_control_evidence(
        result=result,
        current_user="Mañana puedo escribirle al profesor.",
        prior_user="",
    )

    assert verified == result


def test_control_accepts_valid_prior_user_evidence():
    result = {
        "modifiable_components": [],
        "unmodifiable_now": [
            {
                "id": "unmodifiable_1",
                "description": "Las respuestas ya no pueden cambiarse.",
                "evidence": {
                    "quote": "ya no puedo cambiar mis respuestas",
                    "source": "prior_user",
                },
            }
        ],
        "uncertain_outcomes": [],
    }

    verified = _verify_control_evidence(
        result=result,
        current_user="Ahora estoy esperando.",
        prior_user="Ayer entregué el examen y ya no puedo cambiar mis respuestas.",
    )

    assert verified == result


def test_control_rejects_invented_evidence():
    result = {
        "modifiable_components": [
            {
                "id": "modifiable_1",
                "description": "Llamar al profesor.",
                "evidence": {
                    "quote": "El usuario puede llamar mañana al profesor",
                    "source": "current_user",
                },
            }
        ],
        "unmodifiable_now": [],
        "uncertain_outcomes": [],
    }

    with pytest.raises(
        AFUserControlExtractorError,
        match="Evidencia literal inválida",
    ):
        _verify_control_evidence(
            result=result,
            current_user="Mañana puedo escribirle al profesor.",
            prior_user="",
        )


def test_control_rejects_current_ai_as_source():
    result = {
        "modifiable_components": [
            {
                "id": "modifiable_1",
                "description": "Escribir al profesor.",
                "evidence": {
                    "quote": "puedes escribir al profesor",
                    "source": "current_ai",
                },
            }
        ],
        "unmodifiable_now": [],
        "uncertain_outcomes": [],
    }

    with pytest.raises(
        AFUserControlExtractorError,
        match="Fuente no permitida",
    ):
        _verify_control_evidence(
            result=result,
            current_user="No sé qué hacer.",
            prior_user="",
        )


def test_control_rejects_unknown_source():
    result = {
        "modifiable_components": [],
        "unmodifiable_now": [],
        "uncertain_outcomes": [
            {
                "id": "uncertain_1",
                "description": "Resultado externo.",
                "evidence": {
                    "quote": "no sé qué va a pasar",
                    "source": "future_user",
                },
            }
        ],
    }

    with pytest.raises(
        AFUserControlExtractorError,
        match="Fuente de evidencia inválida",
    ):
        _verify_control_evidence(
            result=result,
            current_user="No sé qué va a pasar.",
            prior_user="",
        )


def test_control_accepts_empty_categories():
    result = {
        "modifiable_components": [],
        "unmodifiable_now": [],
        "uncertain_outcomes": [],
    }

    verified = _verify_control_evidence(
        result=result,
        current_user="Hoy me siento tranquilo.",
        prior_user="",
    )

    assert verified == result


def test_control_rejects_non_list_category():
    result = {
        "modifiable_components": {},
        "unmodifiable_now": [],
        "uncertain_outcomes": [],
    }

    with pytest.raises(
        AFUserControlExtractorError,
        match="no contiene una lista válida",
    ):
        _verify_control_evidence(
            result=result,
            current_user="Texto cualquiera.",
            prior_user="",
        )


def test_control_rejects_missing_evidence_object():
    result = {
        "modifiable_components": [
            {
                "id": "modifiable_1",
                "description": "Una acción.",
            }
        ],
        "unmodifiable_now": [],
        "uncertain_outcomes": [],
    }

    with pytest.raises(
        AFUserControlExtractorError,
        match="Falta evidencia estructurada",
    ):
        _verify_control_evidence(
            result=result,
            current_user="Una acción.",
            prior_user="",
        )