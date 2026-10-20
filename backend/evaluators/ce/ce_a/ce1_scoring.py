"""CE1: puntuacion deterministica segun rubrica oficial.

Recibe componentes semanticamente verificados.
No realiza extraccion ni asignacion de impacto.
"""

class CE1ScoringError(ValueError):
    pass


def score_ce1(*, primary_coverage, issues, analysis_complete):
    """
    primary_coverage: addressed, partially_addressed,
                      unaddressed
    issues: incidencias verificadas con impact:
            major, minor
    analysis_complete: confirma que se examino toda la
                       respuesta y su relacion contextual.
    """
    if type(analysis_complete) is not bool:
        raise CE1ScoringError("Estado de analisis invalido.")

    if not analysis_complete:
        return {
            "status": "insufficient_evidence",
            "score": None,
            "reason": "Analisis semantico no completado.",
        }

    if primary_coverage not in {
        "addressed",
        "partially_addressed",
        "unaddressed",
    }:
        raise CE1ScoringError(
            "Cobertura principal no verificada."
        )

    if not isinstance(issues, list):
        raise CE1ScoringError("Incidencias invalidas.")

    for issue in issues:
        if (
            not isinstance(issue, dict)
            or set(issue) != {
                "description", "impact", "evidence_verified"
            }
            or not isinstance(issue["description"], str)
            or not issue["description"].strip()
            or issue["impact"] not in {"major", "minor"}
            or issue["evidence_verified"] is not True
        ):
            raise CE1ScoringError(
                "Incidencia no verificada o invalida."
            )

    impacts = {item["impact"] for item in issues}

    # La desviacion total no se infiere de una simple
    # omision: debe verificarse de forma independiente.
    if primary_coverage == "unaddressed":
        return {
            "status": "requires_total_deviation_check",
            "score": None,
            "reason": (
                "No atender la necesidad principal no "
                "demuestra por si solo desviacion total."
            ),
        }

    # Cobertura parcial sin incidencia de pertinencia
    # documentada: no inventar una clasificacion.
    if primary_coverage == "partially_addressed" and not impacts:
        return {
            "status": "requires_relevance_classification",
            "score": None,
            "reason": (
                "Distinguir pertinencia CE1 de "
                "suficiencia CE2."
            ),
        }

    if "major" in impacts:
        return {
            "status": "scored",
            "score": 1,
            "reason": "Fallas importantes de pertinencia.",
        }

    if "minor" in impacts:
        return {
            "status": "scored",
            "score": 2,
            "reason": "Pertinente, con fallas menores.",
        }

    return {
        "status": "scored",
        "score": 3,
        "reason": (
            "Pertinencia completa, sin digresiones "
            "innecesarias verificadas."
        ),
    }
