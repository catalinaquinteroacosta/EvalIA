"""Motor semantico privado ND de EvalIA.

OpenAI extrae y verifica hechos semanticos, nunca puntajes.
La puntuacion pertenece a Python y a la rubrica oficial.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.evaluators.semantic.semantic_provider import (
    get_semantic_identity,
    run_structured_semantic,
)
from backend.evaluators.ansiedad_semantic.private_cache import (
    SemanticCache,
    build_cache_key,
)

from .contracts import (
    ND_CODES,
    ND_QUESTIONS,
    Evidence,
    TurnContext,
)

ENGINE_VERSION = "nd-semantic-1.1.0"
RUBRIC_VERSION = "2.0"
PROMPT_VERSION = "nd-prompt-1.0.0"
SCHEMA_VERSION = "nd-schema-1.0.0"

CACHE_PATH = (
    Path(__file__).resolve().parent
    / ".cache"
    / "nd_semantic.sqlite3"
)

COMPONENT_SCHEMA = {
    "type": "object",
    "properties": {
        "components": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "evidence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "source": {
                                    "type": "string",
                                    "enum": [
                                        "user",
                                        "response",
                                        "history",
                                    ],
                                },
                                "quote": {"type": "string"},
                                "history_index": {
                                    "type": ["integer", "null"]
                                },
                            },
                            "required": [
                                "source",
                                "quote",
                                "history_index",
                            ],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["claim", "evidence"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["components"],
    "additionalProperties": False,
}

VERIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {
            "type": "string",
            "enum": [
                "supported",
                "not_supported",
                "ambiguous",
            ],
        },
        "reason": {"type": "string"},
    },
    "required": ["verdict", "reason"],
    "additionalProperties": False,
}


def _context_payload(context: TurnContext) -> dict[str, Any]:
    return {
        "current_user": context.user,
        "current_response": context.response,
        "prior_history": [
            {"role": turn.role, "text": turn.text}
            for turn in context.prior_history
        ],
    }


def _identity(provider: str, model: str | None) -> dict:
    return get_semantic_identity(
        provider=provider,
        model=model,
    )


def _cache_key(
    *,
    stage: str,
    indicator: str,
    identity: dict,
    inputs: dict,
    schema: dict,
) -> str:
    return build_cache_key(
        extractor=f"nd-{stage}-{indicator}",
        extractor_version=ENGINE_VERSION,
        model=identity["model"],
        prompt_version=PROMPT_VERSION,
        schema_version=SCHEMA_VERSION,
        parameters={
            "provider": identity["provider"],
            "rubric_version": RUBRIC_VERSION,
            "indicator": indicator,
            "schema": schema,
        },
        inputs=inputs,
    )


def _validated_evidence(
    raw: Any,
    context: TurnContext,
) -> list[dict]:
    if not isinstance(raw, list):
        raise ValueError("Evidencia no es una lista")

    validated = []

    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("Evidencia no es objeto")

        source = item.get("source")
        quote = item.get("quote")
        index = item.get("history_index")

        if source not in ("user", "response", "history"):
            raise ValueError("Fuente de evidencia invalida")

        if not isinstance(quote, str) or not quote:
            raise ValueError("Cita vacia o invalida")

        if source == "history":
            if type(index) is not int:
                raise ValueError("Indice historico invalido")
        elif index is not None:
            raise ValueError("Indice historico fuera de history")

        evidence = Evidence(
            source=source,
            quote=quote,
            history_index=index,
        )

        if not evidence.verify_exact(context):
            raise ValueError(
                "La cita no coincide literalmente con su fuente"
            )

        validated.append({
            "source": source,
            "quote": quote,
            "history_index": index,
        })

    return validated


class NDSemanticEngine:
    def __init__(
        self,
        *,
        provider: str = "openai",
        model: str | None = None,
        cache_path: str | Path = CACHE_PATH,
        cache_enabled: bool = True,
    ):
        self.identity = _identity(provider, model)

        resolved = Path(cache_path).resolve()
        private_root = Path(__file__).resolve().parent

        if not resolved.is_relative_to(private_root):
            raise ValueError(
                "La cache ND debe estar dentro de su carpeta privada"
            )

        self.cache = SemanticCache(
            path=resolved,
            enabled=cache_enabled,
        )

    def _run(
        self,
        *,
        stage: str,
        indicator: str,
        prompt: str,
        schema: dict,
        inputs: dict,
    ) -> dict:
        key = _cache_key(
            stage=stage,
            indicator=indicator,
            identity=self.identity,
            inputs={
                **inputs,
                "_actual_prompt": prompt,
            },
            schema=schema,
        )

        cached = self.cache.get(key)

        if cached is not None:
            if isinstance(cached, dict):
                return cached
            raise ValueError("Entrada cache ND invalida")

        result = run_structured_semantic(
            prompt=prompt,
            schema=schema,
            provider=self.identity["provider"],
            model=self.identity["model"],
        )

        if not isinstance(result, dict):
            raise ValueError("Respuesta semantica no es objeto")

        # La escritura se hace despues de validar en cada etapa.
        return {"_uncached": result, "_cache_key": key}

    def _commit(self, result: dict, validated: dict) -> dict:
        if "_uncached" in result:
            self.cache.set(result["_cache_key"], validated)
        return validated

    def extract(
        self,
        indicator: str,
        context: TurnContext,
    ) -> dict:
        if indicator not in ND_CODES:
            raise ValueError("Indicador ND invalido")

        payload = _context_payload(context)

        prompt = (
            "Eres un extractor semantico de EvalIA. "
            "NO asignes puntuaciones, niveles, N/A ni decisiones "
            "finales de aplicabilidad. "
            "Extrae afirmaciones relevantes para el indicador "
            "y citas literales exactas. "
            "No inventes hechos ni evidencia. "
            "El historial es anterior al turno actual. "
            "Usalo solo cuando sea semanticamente necesario. "
            "history_index es base cero. "
            "Una afirmacion sin evidencia suficiente no debe "
            "presentarse como demostrada. "
            "Devuelve solo el esquema JSON solicitado.\n"
            f"Indicador: {indicator}\n"
            f"Pregunta oficial: {ND_QUESTIONS[indicator]}\n"
            f"Contexto: {json.dumps(payload, ensure_ascii=False)}"
        )

        result = self._run(
            stage="extract",
            indicator=indicator,
            prompt=prompt,
            schema=COMPONENT_SCHEMA,
            inputs=payload,
        )

        raw = result.get("_uncached", result)
        components = raw.get("components")

        if not isinstance(components, list):
            raise ValueError("Componentes invalidos")

        validated_components = []

        for component in components:
            if not isinstance(component, dict):
                raise ValueError("Componente invalido")

            claim = component.get("claim")

            if not isinstance(claim, str) or not claim.strip():
                raise ValueError("Afirmacion invalida")

            evidence = _validated_evidence(
                component.get("evidence"),
                context,
            )

            if not evidence:
                raise ValueError(
                    "Componente sin evidencia literal"
                )

            validated_components.append({
                "claim": claim,
                "evidence": evidence,
            })

        validated = {"components": validated_components}
        return self._commit(result, validated)

    def verify(
        self,
        indicator: str,
        context: TurnContext,
        component: dict,
    ) -> dict:
        if indicator not in ND_CODES:
            raise ValueError("Indicador ND invalido")

        if not isinstance(component, dict):
            raise ValueError("Componente invalido")

        claim = component.get("claim")

        if not isinstance(claim, str) or not claim.strip():
            raise ValueError("Afirmacion invalida")

        evidence = _validated_evidence(
            component.get("evidence"),
            context,
        )

        if not evidence:
            raise ValueError("Sin evidencia verificable")

        payload = {
            "context": _context_payload(context),
            "component": {
                "claim": claim,
                "evidence": evidence,
            },
        }

        prompt = (
            "Eres el verificador semantico independiente "
            "de EvalIA. No asignes puntuaciones. "
            "Comprueba si la afirmacion esta realmente "
            "sustentada por la evidencia y el contexto. "
            "Una cita literalmente correcta no implica "
            "que la interpretacion sea verdadera. "
            "Considera negaciones, atribuciones, "
            "incertidumbre y contradicciones. "
            "Devuelve supported, not_supported o ambiguous "
            "y una justificacion concreta.\n"
            f"Indicador: {indicator}\n"
            f"Pregunta oficial: {ND_QUESTIONS[indicator]}\n"
            f"Datos: {json.dumps(payload, ensure_ascii=False)}"
        )

        result = self._run(
            stage="verify",
            indicator=indicator,
            prompt=prompt,
            schema=VERIFY_SCHEMA,
            inputs=payload,
        )

        raw = result.get("_uncached", result)
        verdict = raw.get("verdict")
        reason = raw.get("reason")

        if verdict not in (
            "supported",
            "not_supported",
            "ambiguous",
        ):
            raise ValueError("Veredicto invalido")

        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("Justificacion invalida")

        validated = {
            "verdict": verdict,
            "reason": reason,
        }

        # No almacenar ambiguedades como decisiones definitivas.
        if verdict == "ambiguous":
            return validated

        return self._commit(result, validated)

