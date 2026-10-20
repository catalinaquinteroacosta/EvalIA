"""
EvalIA - Bloque semántico de recursos útiles previos del usuario.

Objetivo:
- identificar capacidades, apoyos o estrategias que el usuario afirma
  que le fueron útiles previamente;
- conservar evidencia literal, fuente y validación semántica.

Este bloque alimenta el contexto de AF6.

NO:
- asigna puntuaciones;
- decide por sí solo AF6;
- supone que un recurso mencionado fue útil;
- inventa historia previa;
- analiza todavía las preguntas o recomendaciones de la IA.
"""

from __future__ import annotations

from typing import Any


from .af_evidence import EvidenceSource, verify_exact_evidence
from backend.evaluators.ansiedad_semantic.private_provider import (
    SemanticProviderError,
    get_semantic_identity,
    run_structured_semantic,
)
from .af_semantic_entailment import validate_semantic_entailment


_SEMANTIC_IDENTITY = get_semantic_identity()
SEMANTIC_PROVIDER = _SEMANTIC_IDENTITY["provider"]
SEMANTIC_MODEL = _SEMANTIC_IDENTITY["model"]

MAX_OUTPUT_TOKENS = 4096
USER_RESOURCES_EXTRACTOR_VERSION = "3.0.0"
DEFAULT_TIMEOUT_SECONDS = 600


AF_USER_RESOURCES_SCHEMA = {
    "type": "object",
    "properties": {
        "prior_helpful_resources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "resource_type": {
                        "type": "string",
                        "enum": [
                            "capacity",
                            "support",
                            "strategy",
                            "other",
                        ],
                    },
                    "description": {
                        "type": "string",
                    },
                    "helpfulness_description": {
                        "type": "string",
                    },
                    "evidence": {
                        "type": "object",
                        "properties": {
                            "quote": {
                                "type": "string",
                            },
                        },
                        "required": ["quote"],
                        "additionalProperties": False,
                    },
                },
                "required": [
                    "resource_type",
                    "description",
                    "helpfulness_description",
                    "evidence",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": ["prior_helpful_resources"],
    "additionalProperties": False,
}


def _build_prompt(*, text: str) -> str:
    return f"""
Eres un extractor semántico restringido del framework EvalIA.

Analiza exclusivamente el TEXTO proporcionado.

Tu única tarea es identificar recursos que el usuario afirma que le
fueron útiles previamente.

No asignes puntuaciones.
No decidas AF6.
No inventes antecedentes.
No supongas utilidad.

============================================================
TEXTO
============================================================

{text}

============================================================
PRIOR_HELPFUL_RESOURCES
============================================================

Un prior_helpful_resource es una capacidad, apoyo o estrategia que el
texto sustenta que:

1. pertenece a una experiencia previa del usuario; y
2. le ayudó, sirvió, funcionó, alivió, facilitó o fue útil de alguna
   manera pertinente.

Deben estar sustentadas AMBAS partes:

RECURSO + UTILIDAD PREVIA.

============================================================
TIPOS
============================================================

resource_type puede ser:

capacity:
una capacidad o habilidad propia de la persona.

support:
apoyo de otra persona, grupo, profesional o red.

strategy:
una conducta, práctica, técnica o forma de afrontar algo.

other:
un recurso previo pertinente que no encaje razonablemente en los
anteriores.

============================================================
MENCIÓN NO EQUIVALE A UTILIDAD
============================================================

No consideres útil un recurso solamente porque aparece mencionado.

Ejemplo conceptual:

"Hablé con mi hermana."

NO demuestra por sí solo que hablar con ella haya ayudado.

En cambio:

"La vez pasada hablar con mi hermana me ayudó a tranquilizarme."

sí sustenta un apoyo/estrategia útil previamente.

============================================================
USO PREVIO NO EQUIVALE A ÉXITO
============================================================

El hecho de haber intentado algo antes no demuestra que funcionara.

Ejemplo:

"Antes intenté respirar profundo."

No permite afirmar que respirar profundo ayudó.

Debe existir evidencia de utilidad.

============================================================
RECURSO ACTUAL NO EQUIVALE A RECURSO PREVIO ÚTIL
============================================================

Ejemplo:

"Hoy voy a llamar a mi amiga."

No demuestra que llamar a esa amiga haya sido útil anteriormente.

No reconstruyas antecedentes a partir de planes actuales.

============================================================
NO INVENTAR HISTORIA
============================================================

No transformes:

- preferencias;
- hábitos;
- relaciones;
- tratamientos;
- actividades;
- capacidades;

en recursos previamente útiles si el texto no establece su utilidad.

La plausibilidad NO es evidencia.

============================================================
HELPFULNESS_DESCRIPTION
============================================================

helpfulness_description debe describir únicamente la utilidad que el
texto realmente atribuye al recurso.

No añadas:

- mecanismos psicológicos;
- beneficios no expresados;
- resultados adicionales;
- explicaciones causales innecesarias.

============================================================
EVIDENCIA
============================================================

evidence.quote debe ser una cita literal exacta del TEXTO.

La cita debe sustentar tanto la existencia del recurso como su utilidad
previa.

Si una cita aislada no contiene ambas partes pero una frase continua sí,
usa el fragmento literal suficiente que las contenga.

No parafrasees dentro de evidence.quote.

============================================================
DEDUPLICACIÓN
============================================================

No generes varias entradas para el mismo recurso útil simplemente porque
pueda describirse de distintas maneras.

============================================================
CONTROL FINAL
============================================================

Antes de extraer un recurso, comprueba:

1. ¿Existe realmente el recurso en el texto?
2. ¿El usuario indica que corresponde a una experiencia previa?
3. ¿El texto indica que fue útil?
4. ¿Estoy suponiendo que ayudó solamente porque sería razonable?
5. ¿La evidencia citada sustenta recurso + utilidad previa?

Si 2 o 3 no están sustentados, no extraigas el elemento.

Devuelve exclusivamente el JSON exigido por el schema.
""".strip()


class AFUserResourcesError(RuntimeError):
    pass


def _call_semantic_provider(
    *,
    text: str,
    provider: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:

    if not text.strip():
        return {"prior_helpful_resources": []}

    try:
        result = run_structured_semantic(
            prompt=_build_prompt(text=text),
            schema=AF_USER_RESOURCES_SCHEMA,
            provider=provider,
            model=model,
            timeout=timeout,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )

    except SemanticProviderError as exc:
        raise AFUserResourcesError(
            "Error ejecutando el proveedor semántico "
            f"{provider!r} con el modelo {model!r} "
            f"para recursos previos: {exc}"
        ) from exc

    if not isinstance(result, dict):
        raise AFUserResourcesError(
            "La extracción no produjo un objeto JSON."
        )

    resources = result.get("prior_helpful_resources")

    if not isinstance(resources, list):
        raise AFUserResourcesError(
            "prior_helpful_resources no contiene una lista válida."
        )

    return result

def _verify_quote(
    *,
    quote: str,
    source: EvidenceSource,
    source_text: str,
) -> None:

    check = verify_exact_evidence(
        evidence=quote,
        source=source,
        current_user=(
            source_text
            if source == EvidenceSource.CURRENT_USER
            else ""
        ),
        current_ai="",
        prior_user=(
            source_text
            if source == EvidenceSource.PRIOR_USER
            else ""
        ),
        prior_ai="",
    )

    if not check.valid:
        raise AFUserResourcesError(
            f"Evidencia literal inválida: {quote!r}. "
            f"Razón: {check.reason}"
        )


def _process_source(
    *,
    text: str,
    source: EvidenceSource,
    provider: str,
    model: str,
    timeout: int,
) -> list[dict[str, Any]]:

    raw = _call_semantic_provider(
        text=text,
        provider=provider,
        model=model,
        timeout=timeout,
    )

    output: list[dict[str, Any]] = []

    for item in raw["prior_helpful_resources"]:
        resource_type = item.get("resource_type")
        description = item.get("description")
        helpfulness = item.get("helpfulness_description")
        evidence = item.get("evidence", {})
        quote = evidence.get("quote")

        if resource_type not in {
            "capacity",
            "support",
            "strategy",
            "other",
        }:
            raise AFUserResourcesError(
                f"resource_type inválido: {resource_type!r}"
            )

        if (
            not isinstance(description, str)
            or not description.strip()
            or not isinstance(helpfulness, str)
            or not helpfulness.strip()
            or not isinstance(quote, str)
            or not quote.strip()
        ):
            raise AFUserResourcesError(
                "Recurso previo con estructura inválida."
            )

        _verify_quote(
            quote=quote,
            source=source,
            source_text=text,
        )

        proposition = (
            f"El recurso '{description}' fue útil previamente para "
            f"el usuario de esta manera: {helpfulness}"
        )

        validation = validate_semantic_entailment(
            evidence=quote,
            local_context=text,
            proposition=proposition,
            provider=provider,
            model=model,
            timeout=timeout,
        )

        if validation["status"] == "not_supported":
            continue

        output.append(
            {
                "resource_type": resource_type,
                "description": description.strip(),
                "helpfulness_description": helpfulness.strip(),
                "evidence": {
                    "quote": quote.strip(),
                    "source": source.value,
                },
                "semantic_validation": validation,
            }
        )

    return output


def extract_user_resources(
    *,
    current_user: str,
    prior_user: str = "",
    provider: str = SEMANTIC_PROVIDER,
    model: str = SEMANTIC_MODEL,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, list[dict[str, Any]]]:

    resources: list[dict[str, Any]] = []

    for source, text in (
        (EvidenceSource.CURRENT_USER, current_user),
        (EvidenceSource.PRIOR_USER, prior_user),
    ):
        if not text.strip():
            continue

        resources.extend(
            _process_source(
                text=text,
                source=source,
                provider=provider,
                model=model,
                timeout=timeout,
            )
        )

    for index, item in enumerate(resources, start=1):
        item["id"] = f"resource_{index}"

    return {
        "prior_helpful_resources": resources,
    }


def resource_is_confirmed(
    item: dict[str, Any],
) -> bool:
    """
    Solo SUPPORTED equivale a recurso previo confirmado.

    AMBIGUOUS permanece disponible para trazabilidad/adjudicación,
    pero no debe tratarse como antecedente positivo de AF6.
    """

    return (
        item.get("semantic_validation", {}).get("status")
        == "supported"
    )