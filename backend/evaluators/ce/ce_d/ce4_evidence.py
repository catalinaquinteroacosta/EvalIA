"""Validación de evidencia y r?brica oficial CE4."""

from .ce4_scoring import ContractError
from .ce4_rubric_verification import verify_rubric_execution


REQUIRED = {
    "analysis_complete",
    "full_response_audited",
    "applicable",
    "applicability_evidence",
    "rubric_execution",
    "claims",
}



def _resolve_verdict(
    *,
    verify_claim,
    original,
    quote,
    condition,
    component,
    reconcile_claim=None,
):
    verdict = verify_claim(original, quote, condition)

    if verdict == "supported":
        return "supported"

    if verdict not in ("unsupported", "not_supported", "ambiguous"):
        return "blocked"

    if reconcile_claim is None:
        return "blocked"

    try:
        reconciled = reconcile_claim(
            original,
            quote,
            condition,
            component,
        )
    except Exception:
        return "blocked"

    if reconciled != "supported":
        return "blocked"

    # La segunda pasada debe aportar respaldo independiente.
    # No transforma automaticamente la primera discrepancia
    # en una aprobacion definitiva.
    if verdict in ("unsupported", "not_supported"):
        return "blocked"

    return "supported"


def _blocked(component):
    return {
        "status": "BLOCKED",
        "score": None,
        "blocked_components": [component],
    }


def _pending():
    return {"status": "insufficient_evidence", "score": None}


def validate_ce4_evidence(
    *, user_text, response_text, extraction, verify_claim,
    reconcile_claim=None
):
    if not isinstance(user_text, str) or not user_text.strip():
        raise ContractError("Falta usuario")
    if not isinstance(response_text, str) or not response_text.strip():
        raise ContractError("Falta respuesta")
    if not isinstance(extraction, dict) or not callable(verify_claim):
        raise ContractError("Contrato inválido")
    if set(extraction) != REQUIRED:
        raise ContractError("Campos inesperados o ausentes")

    for key in (
        "analysis_complete",
        "full_response_audited",
        "applicable",
    ):
        if type(extraction[key]) is not bool:
            raise ContractError("Estado inválido")

    if not (
        extraction["analysis_complete"]
        and extraction["full_response_audited"]
    ):
        return _pending()

    applicability = extraction["applicability_evidence"]
    if (
        not isinstance(applicability, dict)
        or set(applicability)
        != {"source", "quote", "interpretation"}
    ):
        raise ContractError("Evidencia de aplicabilidad inválida")

    quote = applicability["quote"]
    if (
        applicability["source"] != "response"
        or not isinstance(quote, str)
        or not quote.strip()
        or quote not in response_text
    ):
        return _pending()

    interpretation = applicability["interpretation"]
    if (
        not isinstance(interpretation, str)
        or not interpretation.strip()
    ):
        raise ContractError("Interpretación inválida")

    claims = extraction["claims"]
    if not isinstance(claims, list):
        raise ContractError("Claims inválidas")

    # Validación literal completa antes de llamadas semánticas.
    if extraction["applicable"] and not claims:
        return _pending()

    for claim in claims:
        if (
            not isinstance(claim, dict)
            or set(claim) != {"source", "quote", "interpretation"}
        ):
            raise ContractError("Claim inválida")

        source = claim["source"]
        if source not in ("user", "response"):
            raise ContractError("Fuente inválida")

        original = (
            user_text if source == "user" else response_text
        )

        claim_quote = claim["quote"]
        if (
            not isinstance(claim_quote, str)
            or not claim_quote.strip()
            or claim_quote not in original
        ):
            return _pending()

        claim_interpretation = claim["interpretation"]
        if (
            not isinstance(claim_interpretation, str)
            or not claim_interpretation.strip()
        ):
            raise ContractError("Interpretación inválida")

    condition = (
        "CE4 APLICABILIDAD. Comprueba independientemente "
        "si la extensión de la respuesta completa hace "
        "necesaria una estructura visual en este contexto. "
        "No deduzcas aplicabilidad de la presencia o ausencia "
        "de listas o párrafos. Tampoco de que el usuario "
        "solicite pasos. La afirmación extraída es: "
        + (
            "SÍ necesita estructura visual. "
            if extraction["applicable"]
            else "NO necesita estructura visual. "
        )
        + "Justificación: "
        + interpretation
        + ". Busca contraevidencia. No puntúes."
    )

    verdict = _resolve_verdict(
        verify_claim=verify_claim,
        original=response_text,
        quote=response_text,
        condition=condition,
        component="applicability",
        reconcile_claim=reconcile_claim,
    )

    if verdict != "supported":
        return _blocked("applicability")

    if not extraction["applicable"]:
        return {"status": "not_applicable", "score": None}

    for claim_index, claim in enumerate(claims):
        original = (
            user_text
            if claim["source"] == "user"
            else response_text
        )

        verdict = _resolve_verdict(
            verify_claim=verify_claim,
            original=original,
            quote=claim["quote"],
            condition=(
                "CE4. Verifica independientemente esta "
                "interpretacion sin puntuar: "
                + claim["interpretation"]
            ),
            component="claim:" + str(claim_index),
            reconcile_claim=reconcile_claim,
        )

        if verdict != "supported":
            return _blocked("claim:" + str(claim_index))

    return verify_rubric_execution(
        response_text=response_text,
        applicable=True,
        analysis_complete=True,
        execution=extraction["rubric_execution"],
        verify_claim=verify_claim,
        reconcile_claim=reconcile_claim,
    )
