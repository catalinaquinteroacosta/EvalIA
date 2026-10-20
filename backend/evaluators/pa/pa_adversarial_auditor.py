
"""Auditoria independiente PA6/PA8 sin puntuacion."""

AUDIT_PROMPT = """
Eres un auditor semantico independiente.
Usa la pregunta oficial como autoridad.
No asignes puntuaciones.

Examina el contexto original y las conclusiones
del extractor y del verificador.

PA6:
Distingue acciones acumulativas, opciones reales
y adaptabilidad. Una lista no demuestra por si sola
alternativas, pero tampoco las excluye.

PA8:
Distingue revisar preocupaciones de revisar
resultados de una accion o ajustar un plan.
Respeta la disyuncion 'o' de la pregunta oficial.

No impongas requisitos adicionales.
Si la conclusion no esta sustentada, contradicted.
Si hay incertidumbre material, uncertain.

Devuelve JSON:
{
 "verdict": "supported|contradicted|uncertain",
 "reason": "explicacion",
 "material_issue": null
}
"""

def audit_indicator(client, ask, item, context, extracted, checked):
    code = item.get("code")

    if code not in ("PA6", "PA8"):
        return None

    result = ask(
        client,
        AUDIT_PROMPT,
        {
            "indicator": item,
            "context": context,
            "extraction": extracted,
            "verification": checked,
        },
    )

    if not isinstance(result, dict):
        raise ValueError("Invalid adversarial response")

    if result.get("verdict") not in (
        "supported", "contradicted", "uncertain"
    ):
        raise ValueError("Invalid adversarial verdict")

    if not isinstance(result.get("reason"), str) or not result["reason"].strip():
        raise ValueError("Missing adversarial reason")

    return result
