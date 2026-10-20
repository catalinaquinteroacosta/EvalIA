from __future__ import annotations

"""
Validacion de evidencia literal para EM.

Responsabilidad unica:
- comprobar que una cita declarada por el extractor existe literalmente
  en alguna de las fuentes permitidas;
- identificar de que fuente procede;
- rechazar citas inventadas, corregidas o parafraseadas.

Este modulo:
- NO interpreta semantica;
- NO asigna puntuaciones;
- NO decide aplicabilidad;
- NO corrige evidencia;
- NO usa matching aproximado.
"""

from dataclasses import dataclass
from typing import Iterable


EM_EVIDENCE_VERSION = "EM-EVIDENCE-1.0.0"

SOURCE_PREVIOUS = "previous_context"
SOURCE_USER = "user_message"
SOURCE_AI = "ai_response"

ALLOWED_SOURCES = (
    SOURCE_PREVIOUS,
    SOURCE_USER,
    SOURCE_AI,
)


@dataclass(frozen=True)
class EvidenceMatch:
    quote: str
    source: str
    start: int
    end: int


@dataclass(frozen=True)
class EvidenceValidation:
    valid: bool
    matches: tuple[EvidenceMatch, ...]
    invalid_quotes: tuple[str, ...]


def _normalize_input(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def build_sources(
    previous_context: str = "",
    user_message: str = "",
    ai_response: str = "",
) -> dict[str, str]:
    return {
        SOURCE_PREVIOUS: _normalize_input(previous_context),
        SOURCE_USER: _normalize_input(user_message),
        SOURCE_AI: _normalize_input(ai_response),
    }


def find_exact_quote(
    quote: str,
    *,
    previous_context: str = "",
    user_message: str = "",
    ai_response: str = "",
) -> tuple[EvidenceMatch, ...]:
    """
    Busca coincidencias literales exactas.

    No hace:
    - lower()
    - strip() sobre el contenido de la cita
    - normalizacion Unicode
    - correccion ortografica
    - fuzzy matching
    - regex semantico
    """

    if not isinstance(quote, str):
        return ()

    if quote == "":
        return ()

    sources = build_sources(
        previous_context=previous_context,
        user_message=user_message,
        ai_response=ai_response,
    )

    matches: list[EvidenceMatch] = []

    for source_name in ALLOWED_SOURCES:
        text = sources[source_name]

        start = 0

        while True:
            index = text.find(quote, start)

            if index < 0:
                break

            matches.append(
                EvidenceMatch(
                    quote=quote,
                    source=source_name,
                    start=index,
                    end=index + len(quote),
                )
            )

            start = index + 1

    return tuple(matches)


def verify_exact_evidence(
    quotes: Iterable[str],
    *,
    previous_context: str = "",
    user_message: str = "",
    ai_response: str = "",
) -> EvidenceValidation:
    """
    Valida que TODAS las citas no vacias existan literalmente.

    Una sola cita inventada/parafraseada hace que valid=False.
    """

    matches: list[EvidenceMatch] = []
    invalid: list[str] = []

    for quote in quotes:
        if not isinstance(quote, str) or quote == "":
            invalid.append(
                quote if isinstance(quote, str) else repr(quote)
            )
            continue

        found = find_exact_quote(
            quote,
            previous_context=previous_context,
            user_message=user_message,
            ai_response=ai_response,
        )

        if not found:
            invalid.append(quote)
            continue

        matches.extend(found)

    return EvidenceValidation(
        valid=not invalid,
        matches=tuple(matches),
        invalid_quotes=tuple(invalid),
    )


def validate_component_evidence(
    component: dict,
    *,
    previous_context: str = "",
    user_message: str = "",
    ai_response: str = "",
) -> dict:
    """
    Valida evidence y counterevidence de un componente extraido.

    Devuelve datos de trazabilidad; no cambia value y no interpreta
    si la afirmacion semantica es correcta.
    """

    evidence = component.get("evidence", [])
    counterevidence = component.get("counterevidence", [])

    if not isinstance(evidence, list):
        raise TypeError("component['evidence'] debe ser list")

    if not isinstance(counterevidence, list):
        raise TypeError("component['counterevidence'] debe ser list")

    evidence_result = verify_exact_evidence(
        evidence,
        previous_context=previous_context,
        user_message=user_message,
        ai_response=ai_response,
    )

    counter_result = verify_exact_evidence(
        counterevidence,
        previous_context=previous_context,
        user_message=user_message,
        ai_response=ai_response,
    )

    return {
        "evidence_valid": evidence_result.valid,
        "counterevidence_valid": counter_result.valid,
        "evidence_matches": evidence_result.matches,
        "counterevidence_matches": counter_result.matches,
        "invalid_evidence": evidence_result.invalid_quotes,
        "invalid_counterevidence": counter_result.invalid_quotes,
    }
