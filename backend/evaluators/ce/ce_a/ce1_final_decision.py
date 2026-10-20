"""CE1: integracion y control de la decision automatica."""

from .ce1_impact_verifier import CE1IndependentVerificationError
from .ce1_integrated import evaluate_ce1_integrated
from .ce1_relevance_classifier import classify_ce1_relevance
from .ce1_scoring import score_ce1


def _pending(reason, evidence=None):
    return {
        "status": "insufficient_evidence",
        "score": None,
        "reason": reason,
        "evidence": evidence,
    }


def decide_ce1(
    *,
    user_text,
    response_text,
    prior_context="",
    extraction=None,
    model=None,
    use_cache=True,
):
    integrated = evaluate_ce1_integrated(
        user_text=user_text,
        response_text=response_text,
        prior_context=prior_context,
        extraction=extraction,
        model=model,
        use_cache=use_cache,
    )

    if integrated["status"] != "evidence_integrated":
        return _pending(
            "Los controles previos no estan completos.",
            integrated,
        )

    coverage = integrated["primary_coverage"]

    if coverage not in {
        "addressed",
        "partially_addressed",
        "unaddressed",
    }:
        return _pending(
            "Cobertura principal no concluyente.",
            integrated,
        )

    fragments = []

    for item in integrated["fragments"]:
        verification = item["verification"]

        if (
            verification["status"] != "verified"
            or not verification["decision"]["verified"]
        ):
            return _pending(
                "Fragmento sin verificacion completa.",
                item,
            )

        fragments.append({
            "interpretation": verification["interpretation"],
            "evidence": verification["evidence"],
            "verdict": verification["decision"]["verdict"],
        })

    try:
        classification = classify_ce1_relevance(
            primary_need=integrated["primary_need"],
            primary_coverage=coverage,
            verified_fragments=fragments,
            user_text=user_text,
            response_text=response_text,
            prior_context=prior_context,
            model=model,
        )
    except CE1IndependentVerificationError as exc:
        return _pending("Verificacion independiente CE1 no concluyente: " + str(exc))

    if not classification["analysis_complete"]:
        return _pending(
            "Clasificacion semantica incompleta.",
            classification,
        )

    relevance = classification["primary_relevance"]
    total = classification["total_deviation"]

    if relevance == "ambiguous":
        return _pending(
            "Pertinencia global no concluyente.",
            classification,
        )

    # Un fragmento que atiende directamente una necesidad
    # no demuestra por si solo que atienda la principal.
    # La cobertura principal verificada tiene prioridad.
    if total and coverage != "unaddressed":
        return _pending(
            "Contradiccion: desviacion total y "
            "necesidad principal atendida.",
            classification,
        )

    if total and relevance != "unrelated":
        return _pending(
            "Desviacion total contradictoria.",
            classification,
        )

    if relevance == "fully_related" and total:
        return _pending(
            "Pertinencia completa incompatible "
            "con desviacion total.",
            classification,
        )

    unnecessary = [
        item for item in fragments
        if item["verdict"] == "unnecessary_digression"
    ]

    issues = classification["issues"]

    # El clasificador no puede ignorar una digresion
    # innecesaria confirmada por los controles previos.
    for fragment in unnecessary:
        if not any(
            fragment["evidence"] == issue["evidence"]
            for issue in issues
        ):
            return _pending(
                "Digresion verificada sin impacto "
                "clasificado.",
                fragment,
            )

    # No se acepta una incidencia cuya cita contradiga
    # directamente la clasificacion contextual verificada.
    for issue in issues:
        matching = [
            fragment for fragment in fragments
            if fragment["evidence"] == issue["evidence"]
        ]

        if matching and all(
            fragment["verdict"] in {
                "relevant",
                "useful_complement",
            }
            for fragment in matching
        ):
            return _pending(
                "Incidencia incompatible con "
                "fragmento pertinente verificado.",
                issue,
            )

    # Una cita existente en la respuesta no demuestra
    # por si sola una falla de pertinencia.
    # Debe coincidir con una digresion verificada.
    for issue in issues:
        evidence = issue["evidence"]

        if evidence in response_text:
            supported = any(
                fragment["verdict"] == "unnecessary_digression"
                and fragment["evidence"] == evidence
                for fragment in fragments
            )
            if not supported:
                return _pending(
                    "Incidencia de la respuesta sin "
                    "digresion verificada.",
                    issue,
                )

        elif (
            evidence not in user_text
            and evidence not in prior_context
        ):
            return _pending(
                "Incidencia sin procedencia literal.",
                issue,
            )

    if total:
        # El nivel cero exige una desviacion TOTAL
        # confirmada y ausencia de cobertura principal.
        return {
            "status": "scored",
            "score": 0,
            "rubric_condition": (
                "Se desvia totalmente de "
                "la necesidad principal."
            ),
            "integrated": integrated,
            "classification": classification,
        }

    if relevance == "unrelated":
        return _pending(
            "Respuesta no relacionada sin "
            "desviacion total confirmada.",
            classification,
        )

    if any(
        issue["impact"] == "ambiguous"
        for issue in issues
    ):
        return _pending(
            "Impacto de pertinencia no concluyente.",
            classification,
        )

    if (
        relevance == "partially_related"
        and not issues
    ):
        return _pending(
            "Pertinencia parcial sin fallas "
            "documentadas.",
            classification,
        )

    if (
        relevance == "fully_related"
        and not issues
        and coverage == "unaddressed"
    ):
        return _pending(
            "Pertinencia completa incompatible "
            "con ausencia de cobertura principal.",
            classification,
        )

    verified_issues = [
        {
            "description": issue["description"],
            "impact": issue["impact"],
            "evidence_verified": True,
        }
        for issue in issues
    ]

    # Las omisiones propias de CE2 no reducen CE1.
    # La cobertura parcial solo impide el 3 cuando
    # existe una falla real de pertinencia.
    scoring_coverage = coverage

    if (
        coverage == "partially_addressed"
        and relevance == "fully_related"
        and not issues
        and not unnecessary
    ):
        scoring_coverage = "addressed"

    scored = score_ce1(
        primary_coverage=scoring_coverage,
        issues=verified_issues,
        analysis_complete=True,
    )

    if scored["status"] != "scored":
        return _pending(
            scored["reason"],
            classification,
        )

    # El nivel maximo exige comprobacion positiva:
    # pertinencia completa y ninguna digresion.
    if scored["score"] == 3 and (
        relevance != "fully_related"
        or unnecessary
    ):
        return _pending(
            "No se demostraron todas las "
            "condiciones del nivel maximo.",
            classification,
        )

    # La clasificacion global y el impacto deben
    # describir coherentemente el mismo resultado.
    if (
        scored["score"] in {1, 2}
        and relevance == "fully_related"
    ):
        return _pending(
            "Pertinencia global completa incompatible "
            "con una falla de pertinencia verificada.",
            classification,
        )

    return {
        "status": "scored",
        "score": scored["score"],
        "rubric_condition": scored["reason"],
        "integrated": integrated,
        "classification": classification,
    }
