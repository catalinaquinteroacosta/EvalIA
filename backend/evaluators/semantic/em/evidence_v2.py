from __future__ import annotations

"""
Evidencia literal trazable para EM.

Esta capa SOLO valida procedencia y literalidad.

NO:
- interpreta semantica;
- decide aplicabilidad;
- puntua;
- busca una cita en otra fuente para rescatar una atribucion incorrecta;
- inventa evidencia para ausencias.
"""

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from backend.evaluators.semantic.em.temporal_context import (
    HistoryMessage,
    get_history_message,
    normalize_prior_history,
)


EM_EVIDENCE_V2_VERSION = "EM-EVIDENCE-2.0.0"

SOURCE_HISTORY = "history"
SOURCE_USER = "user"
SOURCE_RESPONSE = "response"

ALLOWED_SOURCES = frozenset({
    SOURCE_HISTORY,
    SOURCE_USER,
    SOURCE_RESPONSE,
})


@dataclass(frozen=True)
class EvidenceRef:
    source: str
    history_index: int | None
    quote: str


@dataclass(frozen=True)
class EvidenceCheck:
    valid: bool
    evidence: EvidenceRef
    resolved_role: str | None
    start: int | None
    end: int | None
    error: str | None


def parse_evidence_ref(value: EvidenceRef | Mapping[str, Any]) -> EvidenceRef:
    if isinstance(value, EvidenceRef):
        ref = value

    elif isinstance(value, Mapping):
        if set(value) != {"source", "history_index", "quote"}:
            raise ValueError(
                "La evidencia debe contener exactamente "
                "source, history_index y quote"
            )

        ref = EvidenceRef(
            source=value["source"],
            history_index=value["history_index"],
            quote=value["quote"],
        )

    else:
        raise TypeError(
            "La evidencia debe ser EvidenceRef o mapping"
        )

    if ref.source not in ALLOWED_SOURCES:
        raise ValueError(
            f"source invalido: {ref.source!r}"
        )

    if not isinstance(ref.quote, str):
        raise TypeError("quote debe ser str")

    if ref.quote == "":
        raise ValueError(
            "quote no puede ser vacio; una ausencia se audita "
            "sin fabricar evidencia"
        )

    if ref.source == SOURCE_HISTORY:
        if (
            isinstance(ref.history_index, bool)
            or not isinstance(ref.history_index, int)
        ):
            raise ValueError(
                "source='history' exige history_index int base 0"
            )

        if ref.history_index < 0:
            raise ValueError(
                "history_index no puede ser negativo"
            )

    else:
        if ref.history_index is not None:
            raise ValueError(
                f"source={ref.source!r} exige history_index=null"
            )

    return ref


def _current_text(
    source: str,
    *,
    user_message: str,
    ai_response: str,
) -> str:
    if source == SOURCE_USER:
        return user_message

    if source == SOURCE_RESPONSE:
        return ai_response

    raise ValueError(
        "_current_text solo admite user/response"
    )


def verify_evidence_ref(
    evidence: EvidenceRef | Mapping[str, Any],
    *,
    prior_history: Sequence[
        HistoryMessage | Mapping[str, object]
    ] | None = None,
    user_message: str = "",
    ai_response: str = "",
) -> EvidenceCheck:
    """
    Comprueba la cita EXCLUSIVAMENTE en la fuente declarada.

    Si source=history:
    solo busca en prior_history[history_index].text.

    Una coincidencia en otro turno o fuente NO rescata la evidencia.
    """
    ref = parse_evidence_ref(evidence)

    if not isinstance(user_message, str):
        raise TypeError("user_message debe ser str")

    if not isinstance(ai_response, str):
        raise TypeError("ai_response debe ser str")

    resolved_role: str | None = None

    if ref.source == SOURCE_HISTORY:
        try:
            message = get_history_message(
                prior_history,
                ref.history_index,  # type: ignore[arg-type]
            )
        except (IndexError, TypeError, ValueError) as exc:
            return EvidenceCheck(
                valid=False,
                evidence=ref,
                resolved_role=None,
                start=None,
                end=None,
                error=f"invalid_history_index:{exc}",
            )

        text = message.text
        resolved_role = message.role

    else:
        # Validamos tambien el historial aunque no se utilice como evidencia:
        # si se suministra, debe respetar el contrato temporal.
        normalize_prior_history(prior_history)

        text = _current_text(
            ref.source,
            user_message=user_message,
            ai_response=ai_response,
        )

    start = text.find(ref.quote)

    if start < 0:
        return EvidenceCheck(
            valid=False,
            evidence=ref,
            resolved_role=resolved_role,
            start=None,
            end=None,
            error="quote_not_found_in_declared_source",
        )

    return EvidenceCheck(
        valid=True,
        evidence=ref,
        resolved_role=resolved_role,
        start=start,
        end=start + len(ref.quote),
        error=None,
    )


def verify_evidence_refs(
    evidence: Sequence[EvidenceRef | Mapping[str, Any]],
    *,
    prior_history: Sequence[
        HistoryMessage | Mapping[str, object]
    ] | None = None,
    user_message: str = "",
    ai_response: str = "",
) -> tuple[EvidenceCheck, ...]:
    if isinstance(evidence, (str, bytes)):
        raise TypeError(
            "evidence debe ser secuencia de referencias, no str"
        )

    return tuple(
        verify_evidence_ref(
            item,
            prior_history=prior_history,
            user_message=user_message,
            ai_response=ai_response,
        )
        for item in evidence
    )


def evidence_refs_are_literal(
    evidence: Sequence[EvidenceRef | Mapping[str, Any]],
    *,
    prior_history: Sequence[
        HistoryMessage | Mapping[str, object]
    ] | None = None,
    user_message: str = "",
    ai_response: str = "",
) -> bool:
    checks = verify_evidence_refs(
        evidence,
        prior_history=prior_history,
        user_message=user_message,
        ai_response=ai_response,
    )

    return all(check.valid for check in checks)


def validate_component_evidence_v2(
    component: Mapping[str, Any],
    *,
    prior_history: Sequence[
        HistoryMessage | Mapping[str, object]
    ] | None = None,
    user_message: str = "",
    ai_response: str = "",
) -> dict[str, Any]:
    evidence = component.get("evidence", [])
    counterevidence = component.get("counterevidence", [])

    if not isinstance(evidence, list):
        raise TypeError("component['evidence'] debe ser list")

    if not isinstance(counterevidence, list):
        raise TypeError("component['counterevidence'] debe ser list")

    evidence_checks = verify_evidence_refs(
        evidence,
        prior_history=prior_history,
        user_message=user_message,
        ai_response=ai_response,
    )

    counter_checks = verify_evidence_refs(
        counterevidence,
        prior_history=prior_history,
        user_message=user_message,
        ai_response=ai_response,
    )

    return {
        "evidence_valid": all(
            check.valid for check in evidence_checks
        ),
        "counterevidence_valid": all(
            check.valid for check in counter_checks
        ),
        "evidence_checks": evidence_checks,
        "counterevidence_checks": counter_checks,
    }
