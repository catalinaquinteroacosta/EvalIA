"""Contrato de polaridad para hechos semanticos ND."""

from dataclasses import dataclass

from .nd99_observation_bridge import FactObservation


@dataclass(frozen=True)
class PolarityFinding:
    fact_name: str
    verdict: str
    quote: str
    reason: str
    complete_response_examined: bool


def reconcile_polarity(
    fact_name: str,
    extraction: PolarityFinding,
    verification: PolarityFinding,
    response: str,
) -> FactObservation:
    """Reconcilia afirmaciones positivas, sin inferir ausencias."""

    if (
        extraction.fact_name != fact_name
        or verification.fact_name != fact_name
    ):
        raise ValueError("Identidad del hecho incorrecta")

    valid = {"supported", "not_supported", "ambiguous"}

    for finding in (extraction, verification):
        if finding.verdict not in valid:
            raise ValueError("Veredicto invalido")

        if not finding.reason.strip():
            raise ValueError("Justificacion vacia")

        if not finding.complete_response_examined:
            raise ValueError("Revision incompleta")

        if finding.quote and finding.quote not in response:
            raise ValueError("Cita literal invalida")

    if (
        extraction.verdict != verification.verdict
        or extraction.verdict == "ambiguous"
    ):
        value = "uncertain"
    elif extraction.verdict == "supported":
        value = "present"
    else:
        # La ausencia no se deduce de unicamente
        # no encontrar evidencia positiva.
        # Se mantiene incierta hasta verificar
        # explicitamente la ausencia en la respuesta.
        value = "uncertain"

    return FactObservation(
        fact_name=fact_name,
        extraction_value=value,
        verification_value=value,
        extraction_quote=extraction.quote,
        verification_quote=verification.quote,
        extraction_reason=extraction.reason,
        verification_reason=verification.reason,
        full_response_examined=(
            extraction.complete_response_examined
            and verification.complete_response_examined
        ),
    )
