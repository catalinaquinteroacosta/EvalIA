"""Integracion conservadora CE1; no autoriza puntuaciones."""

from .extractor import extract_ce_a, validate_extraction
from .coverage_auditor import audit_coverage
from .ce1_coverage_gate import assess_ce1_coverage
from .ce1_need_inventory import build_ce1_need_inventory
from .ce1_primary_identity import verify_primary_identity
from .ce1_primary_group import verify_primary_group
from .need_verifier import verify_need
from .ce1_verified_need_pipeline import evaluate_verified_need
from .ce1_implicit_adapter import evaluate_implicit_need
from .ce1_verified_digression_pipeline import (
    evaluate_verified_digression,
)


def evaluate_ce1_integrated(
    *,
    user_text,
    response_text,
    prior_context="",
    extraction=None,
    model=None,
    use_cache=True,
):
    """Reune controles existentes sin inventar gravedad o niveles."""
    if not isinstance(user_text, str) or not user_text.strip():
        raise ValueError("Mensaje de usuario invalido.")
    if not isinstance(response_text, str) or not response_text.strip():
        raise ValueError("Respuesta invalida.")
    if not isinstance(prior_context, str):
        raise ValueError("Contexto invalido.")

    if extraction is None:
        extraction = extract_ce_a(
            user_text, response_text, prior_context,
            model=model, use_cache=use_cache,
        )

    extraction = validate_extraction(
        extraction, response_text, user_text, prior_context
    )

    result = {
        "status": "review_required",
        "primary_need": extraction["primary_need"],
        "primary_coverage": None,
        "needs": [],
        "fragments": [],
        "coverage_audit": None,
        "pending": [],
        "severity": None,
        "score": None,
        "ready_for_scoring": False,
    }

    coverage = audit_coverage(
        user_text=user_text,
        response_text=response_text,
        prior_context=prior_context,
        extraction=extraction,
        model=model,
        use_cache=use_cache,
    )
    result["coverage_audit"] = coverage

    ce1_coverage = assess_ce1_coverage(coverage)
    result["ce1_coverage"] = ce1_coverage

    if not ce1_coverage["approved"]:
        result["pending"].append({
            "type": "ce1_extraction_coverage",
            "detail": ce1_coverage,
        })
        return result

    inventory = build_ce1_need_inventory(extraction)

    # La identidad de la necesidad principal se verifica
    # semanticamente; la coincidencia textual no es suficiente.
    primary_candidates = []
    identity_trace = []
    result["primary_identity_trace"] = identity_trace

    for entry in inventory:
        need = entry["need"]

        # La procedencia implicita requiere primero resolver
        # de que texto proviene su evidencia.
        if need["source"] == "implicit":
            continue

        identity = verify_primary_identity(
            primary_need=extraction["primary_need"],
            candidate_need=need["need"],
            candidate_source=need["source"],
            candidate_evidence=need["evidence"],
            user_text=user_text,
            prior_context=prior_context,
            model=model,
            use_cache=use_cache,
        )

        identity_trace.append({
            "origin": (entry["origin_field"], entry["origin_index"]),
            "candidate_need": need["need"],
            "candidate_evidence": need["evidence"],
            "verification": identity,
        })

        if identity["verdict"] == "ambiguous":
            result["pending"].append({
                "type": "primary_identity_ambiguity",
                "origin": (
                    entry["origin_field"],
                    entry["origin_index"],
                ),
                "detail": identity,
            })
        elif identity["verdict"] == "confirmed":
            primary_candidates.append((entry, identity))

    # La agrupacion no reemplaza la identidad individual ni resuelve
    # ambiguedades pendientes. Nunca se elige arbitrariamente uno.
    primary_keys = set()
    if len(primary_candidates) > 1 and not result["pending"]:
        try:
            group = verify_primary_group(
                primary_need=extraction["primary_need"],
                candidates=[{
                    "need": entry["need"]["need"],
                    "source": entry["need"]["source"],
                    "evidence": entry["need"]["evidence"],
                } for entry, _ in primary_candidates],
                user_text=user_text, prior_context=prior_context,
                model=model, use_cache=use_cache,
            )
        except ValueError as exc:
            result["pending"].append({
                "type": "primary_group_contract", "detail": str(exc),
            })
        else:
            result["primary_group"] = group
            if group["verdict"] == "single_composite":
                primary_keys = {
                    (entry["origin_field"], entry["origin_index"])
                    for entry, _ in primary_candidates
                }
            else:
                result["pending"].append({
                    "type": "primary_group_unresolved", "detail": group,
                })

    if len(primary_candidates) == 1 and not result["pending"]:
        primary, primary_identity = primary_candidates[0]
        result["primary_identity"] = primary_identity
        primary_keys = {(primary["origin_field"], primary["origin_index"])}

    if not primary_keys or result["pending"]:
        result["pending"].append({
            "type": "primary_need_identity",
            "detail": "La identidad principal no quedo establecida de manera unica.",
            "confirmed_candidates": len(primary_candidates),
        })
        return result

    primary_coverages = []

    for entry in inventory:
        need = entry["need"]
        key = (entry["origin_field"], entry["origin_index"])

        if need["source"] == "implicit":
            contextual = extraction["contextual_needs"][
                entry["origin_index"]
            ]
            try:
                checked = evaluate_implicit_need(
                    contextual,
                    user_text=user_text,
                    response_text=response_text,
                    prior_context=prior_context,
                    model=model,
                    use_cache=use_cache,
                )
            except ValueError as exc:
                result["pending"].append({
                    "type": "implicit_need",
                    "origin": key,
                    "detail": str(exc),
                })
                continue
            coverage_result = checked["coverage"]
            verdict = coverage_result["coverage"]
        else:
            original = {
                "interpretation": need["need"],
                "source": need["source"],
                "evidence": need["evidence"],
                "justification": need["explanation"],
            }
            legitimacy = verify_need(
                original,
                user_text=user_text,
                prior_context=prior_context,
                model=model,
                use_cache=use_cache,
            )
            if legitimacy["verdict"] != "supported":
                result["pending"].append({
                    "type": "need_legitimacy",
                    "origin": key,
                    "detail": legitimacy,
                })
                continue

            try:
                coverage_result = evaluate_verified_need(
                    need,
                    user_text=user_text,
                    response_text=response_text,
                    prior_context=prior_context,
                    model=model,
                    use_cache=use_cache,
                )
            except ValueError as exc:
                result["pending"].append({
                    "type": "need_verification",
                    "origin": key,
                    "detail": str(exc),
                })
                continue
            verdict = coverage_result["coverage"]

        record = {
            "origin": key,
            "source": need["source"],
            "need": need["need"],
            "coverage": verdict,
            "verification": coverage_result,
            "is_primary": key in primary_keys,
        }
        result["needs"].append(record)

        if key in primary_keys:
            primary_coverages.append(verdict)

    # Para una unidad compuesta, ningun componente puede desaparecer.
    # Coberturas mixtas no se convierten automaticamente en una nota CE1.
    if len(primary_coverages) != len(primary_keys):
        result["pending"].append({
            "type": "primary_group_coverage_incomplete",
            "detail": "Falta verificar un componente principal.",
        })
    elif len(primary_keys) == 1:
        result["primary_coverage"] = primary_coverages[0]
    elif len(set(primary_coverages)) == 1:
        result["primary_coverage"] = primary_coverages[0]
    else:
        result["pending"].append({
            "type": "primary_group_mixed_coverage",
            "detail": "Cobertura mixta de componentes; requiere revision.",
            "component_coverages": primary_coverages,
        })

    # Ambos campos son candidatos, NO etiquetas definitivas.
    # El verificador contextual decide la clasificacion.
    seen = set()
    for field in ("ce1_relevant_evidence", "ce1_digressions"):
        for index, item in enumerate(extraction[field]):
            key = (item["interpretation"], item["evidence"])
            if key in seen:
                continue
            seen.add(key)

            checked = evaluate_verified_digression(
                interpretation=item["interpretation"],
                evidence=item["evidence"],
                user_text=user_text,
                response_text=response_text,
                prior_context=prior_context,
                model=model,
                use_cache=use_cache,
            )
            result["fragments"].append({
                "origin": (field, index),
                "verification": checked,
            })
            if checked["status"] != "verified":
                result["pending"].append({
                    "type": "fragment_verification",
                    "origin": (field, index),
                })

    if result["primary_coverage"] is None:
        result["pending"].append({
            "type": "primary_coverage",
            "detail": "La cobertura principal no quedo verificada.",
        })

    # Falta validar identidad semantica de necesidades
    # equivalentes, gravedad y reglas de puntuacion.
    if not result["pending"]:
        result["status"] = "evidence_integrated"

    return result
