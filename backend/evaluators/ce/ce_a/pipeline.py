"""Pipeline CE-A: extracci?n y verificaciones sem?nticas."""

from .extractor import (
    RESPONSE_FIELDS,
    extract_ce_a,
    validate_extraction,
)
from .claim_verifier import verify_claims
from .omission_verifier import verify_omission
from .need_verifier import verify_need
from .coverage_auditor import audit_coverage
from .omission_resolution import resolve_omissions


def evaluate_ce_a_evidence(
    user_text,
    response_text,
    prior_context="",
    *,
    model=None,
    use_cache=True,
    extraction=None,
):
    """Verifica componentes. Nunca asigna puntuaciones."""

    if extraction is None:
        extraction = extract_ce_a(
            user_text=user_text,
            response_text=response_text,
            prior_context=prior_context,
            model=model,
            use_cache=use_cache,
        )

    extraction = validate_extraction(
        extraction,
        response_text,
        user_text,
        prior_context,
    )

    need_checks = []
    evidence_checks = []
    omission_checks = []
    pending = []


    # Adaptar necesidades expl?citas sin modificar
    # la extracci?n original ni perder la cita.
    needs = [
        {
            "interpretation": item["interpretation"],
            "source": "current_user",
            "evidence": item["user_evidence"],
            "justification": "",
        }
        for item in extraction["explicit_needs"]
    ]
    needs.extend(extraction["contextual_needs"])

    for index, need in enumerate(needs):
        verdict = verify_need(
            need,
            user_text=user_text,
            prior_context=prior_context,
            model=model,
            use_cache=use_cache,
        )

        record = {
            "field": "needs",
            "index": index,
            "need": need,
            **verdict,
        }
        need_checks.append(record)

        if verdict["verdict"] != "supported":
            pending.append(record)

    for field in RESPONSE_FIELDS:
        for index, item in enumerate(extraction[field]):
            verdict = verify_claims(
                interpretation=item["interpretation"],
                evidence=item["evidence"],
                response_text=response_text,
                model=model,
                use_cache=use_cache,
            )

            record = {
                "field": field,
                "index": index,
                "interpretation": item["interpretation"],
                "evidence": item["evidence"],
                **verdict,
            }

            evidence_checks.append(record)

            if verdict["verdict"] != "supported":
                pending.append(record)

    for index, item in enumerate(
        extraction["ce2_essential_omissions"]
    ):
        verdict = verify_omission(
            user_text=user_text,
            response_text=response_text,
            prior_context=prior_context,
            missing_information=item["missing_information"],
            context_justification=item["context_justification"],
            model=model,
            use_cache=use_cache,
        )

        record = {
            "field": "ce2_essential_omissions",
            "index": index,
            "missing_information": item["missing_information"],
            "context_justification": item["context_justification"],
            "user_evidence": item["user_evidence"],
            **verdict,
        }

        omission_checks.append(record)

        if verdict["verdict"] not in (
            "supported", "not_supported"
        ):
            pending.append(record)


    coverage = audit_coverage(
        user_text=user_text,
        response_text=response_text,
        prior_context=prior_context,
        extraction=extraction,
        model=model,
        use_cache=use_cache,
    )

    if coverage["verdict"] != "complete":
        pending.append({
            "field": "coverage",
            "verdict": coverage["verdict"],
            "reason": coverage["reason"],
            "findings": coverage["findings"],
        })

    # La ausencia de incidencias detectadas NO equivale
    # todav?a a autorizaci?n para puntuar.
    # A?n faltan: verificar sem?nticamente las necesidades,
    # evaluar cobertura y resolver la r?brica de CE1.
    omission_resolution = None

    checks_complete = (
        coverage["verdict"] == "complete"
        and coverage["findings"] == []
        and not pending
        and all(
            item["verdict"] == "supported"
            for item in need_checks
        )
        and all(
            item["verdict"] == "supported"
            for item in evidence_checks
        )
        and all(
            item["verdict"] in ("supported", "not_supported")
            for item in omission_checks
        )
    )

    if checks_complete:
        omission_resolution = resolve_omissions(
            extraction,
            omission_checks,
        )

    return {
        "omission_resolution": omission_resolution,
        "extraction": extraction,
        "coverage": coverage,
        "need_checks": need_checks,
        "evidence_checks": evidence_checks,
        "omission_checks": omission_checks,
        "pending": pending,
        "ready_for_scoring": False,
        "status": (
            "review_required"
            if pending
            else "partial_validation_complete"
        ),
    }
