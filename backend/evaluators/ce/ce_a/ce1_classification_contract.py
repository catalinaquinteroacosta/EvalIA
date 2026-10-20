"""Contrato de componentes semanticos para CE1.

Este modulo no determina ni asigna puntuaciones.
"""

VALID_IMPACTS = {
    "major",
    "minor",
    "none",
    "ambiguous",
}


class CE1ContractError(ValueError):
    pass


def validate_ce1_classification(data, response_text):
    if not isinstance(data, dict) or set(data) != {
        "primary_need_addressed",
        "primary_need_reason",
        "issues",
        "analysis_complete",
    }:
        raise CE1ContractError("Estructura invalida.")

    if data["primary_need_addressed"] not in {
        "yes", "partially", "no", "ambiguous"
    }:
        raise CE1ContractError("Cobertura principal invalida.")

    if (
        not isinstance(data["primary_need_reason"], str)
        or not data["primary_need_reason"].strip()
        or type(data["analysis_complete"]) is not bool
        or not isinstance(data["issues"], list)
    ):
        raise CE1ContractError("Analisis incompleto o invalido.")

    for item in data["issues"]:
        if not isinstance(item, dict) or set(item) != {
            "description", "evidence", "impact",
            "context_justification",
        }:
            raise CE1ContractError("Incidencia mal estructurada.")

        if item["impact"] not in VALID_IMPACTS:
            raise CE1ContractError("Impacto desconocido.")

        if any(
            not isinstance(item[key], str) or not item[key].strip()
            for key in ("description", "context_justification")
        ):
            raise CE1ContractError("Incidencia sin explicacion.")

        evidence = item["evidence"]
        if (
            not isinstance(evidence, str)
            or not evidence
            or evidence not in response_text
        ):
            raise CE1ContractError("Evidencia no literal.")

    if (
        data["primary_need_addressed"] == "no"
        and not data["issues"]
    ):
        raise CE1ContractError(
            "Desviacion sin incidencia documentada."
        )

    # La incertidumbre se conserva, pero no puede
    # presentarse como un analisis completo.
    if data["analysis_complete"]:
        if data["primary_need_addressed"] == "ambiguous":
            raise CE1ContractError(
                "Necesidad principal ambigua: revision requerida."
            )

        if any(
            item["impact"] == "ambiguous"
            for item in data["issues"]
        ):
            raise CE1ContractError(
                "Impacto ambiguo: revision requerida."
            )

    # Una cobertura parcial necesita una incidencia
    # documentada. Este contrato aun no clasifica
    # las ausencias sin evidencia literal.
    if (
        data["primary_need_addressed"] == "partially"
        and not data["issues"]
    ):
        raise CE1ContractError(
            "Cobertura parcial sin incidencia documentada."
        )

    # Una incidencia sin impacto no puede ser la
    # unica justificacion de una desviacion total.
    if (
        data["primary_need_addressed"] == "no"
        and not any(
            item["impact"] in {"major", "minor", "ambiguous"}
            for item in data["issues"]
        )
    ):
        raise CE1ContractError(
            "Desviacion total sin impacto documentado."
        )

    return data
