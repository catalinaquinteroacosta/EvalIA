# -*- coding: utf-8 -*-
"""
EvalIA - Recuperaci?n sem?ntica segura de evidencia literal.

Permite recuperar desde el texto fuente una cita literal cuando
un extractor produjo una par?frasis sem?nticamente equivalente.

La equivalencia sem?ntica nunca sustituye la trazabilidad:
el valor retornado siempre debe proceder literalmente de la fuente.
"""

from __future__ import annotations

import re

from .af_semantic_entailment import validate_semantic_entailment


LITERAL_EVIDENCE_RECOVERY_VERSION = "1.0.0"


class LiteralEvidenceRecoveryError(RuntimeError):
    """Error controlado de recuperaci?n de evidencia literal."""


def recover_literal_quote(
    *,
    quote: str,
    context: str,
    provider: str,
    model: str,
    timeout: int,
) -> str | None:
    """
    Recupera evidencia exclusivamente como fragmento literal
    del contexto original.

    Si la cita propuesta ya es literal, se conserva.

    Si no lo es, un candidato literal solo puede recuperarse
    cuando sustenta el mismo hecho material completo.

    Compartir tema, palabras o referente no basta.
    El valor retornado siempre procede literalmente del contexto.
    """

    proposed = quote.strip()

    if proposed in context:
        return proposed

    candidates = [
        part.strip()
        for part in re.split(
            r"(?<=[.!?])\s+|\n+",
            context,
        )
        if part.strip()
    ]

    for candidate in candidates:
        relation = validate_semantic_entailment(
            evidence=candidate,
            local_context=candidate,
            proposition=(
                "Eval?a si este fragmento literal del texto "
                "original sustenta sem?nticamente EL MISMO "
                "HECHO MATERIAL COMPLETO que la evidencia "
                "propuesta. Deben conservarse, cuando sean "
                "relevantes, la acci?n o evento, qui?n lo "
                "realiza, el objeto o referente, si la acci?n "
                "ocurre, se interrumpe, contin?a o se completa, "
                "su resultado o desenlace y su negaci?n o "
                "afirmaci?n. Compartir tema, palabras, objeto "
                "o solamente una parte del evento NO basta. "
                "No completes informaci?n ausente ni ignores "
                "contradicciones. Distingue completar una "
                "acci?n exitosamente de interrumpirla o "
                "abandonarla. Una palabra polis?mica no permite "
                "cambiar el sentido material del evento. "
                "Responde supported ?nicamente si este "
                "fragmento puede sustentar la evidencia "
                "propuesta sin cambiar el hecho material "
                "afirmado. Si existe una diferencia material "
                "no resuelta, no debe considerarse supported. "
                f"Evidencia propuesta: {proposed}"
            ),
            provider=provider,
            model=model,
            timeout=timeout,
        )

        if (
            isinstance(relation, dict)
            and relation.get("status") == "supported"
        ):
            if candidate not in context:
                raise LiteralEvidenceRecoveryError(
                    "La recuperaci?n produjo evidencia no literal."
                )

            return candidate

    return None
