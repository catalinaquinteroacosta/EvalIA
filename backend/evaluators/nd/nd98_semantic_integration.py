"""Integracion ND: extraccion y verificacion independiente.

No asigna niveles ni puntuaciones.
"""

from dataclasses import dataclass

from .contracts import ND_CODES, TurnContext, Evidence


@dataclass(frozen=True)
class ComponentDecision:
    claim: str
    status: str
    evidence: tuple[Evidence, ...]
    reason: str


def assess_components(engine, indicator, context):
    if indicator not in ND_CODES:
        raise ValueError("Indicador ND invalido")

    extracted = engine.extract(indicator, context)
    components = extracted.get("components")

    if not isinstance(components, list):
        raise ValueError("Extraccion sin componentes validos")

    decisions = []

    for component in components:
        if not isinstance(component, dict):
            raise ValueError("Componente invalido")

        claim = component.get("claim")
        raw_evidence = component.get("evidence")

        if not isinstance(claim, str) or not claim.strip():
            raise ValueError("Afirmacion invalida")

        if not isinstance(raw_evidence, list) or not raw_evidence:
            raise ValueError("Evidencia invalida")

        evidence = tuple(
            Evidence(
                source=item["source"],
                quote=item["quote"],
                history_index=item.get("history_index"),
            )
            for item in raw_evidence
        )

        if not all(e.verify_exact(context) for e in evidence):
            raise ValueError("Evidencia literal no verificable")

        verified = engine.verify(
            indicator, context, component
        )

        verdict = verified.get("verdict")
        reason = verified.get("reason")

        if verdict not in (
            "supported",
            "not_supported",
            "ambiguous",
        ):
            raise ValueError("Veredicto invalido")

        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("Justificacion invalida")

        status = (
            "VERIFIED"
            if verdict == "supported"
            else "BLOCKED"
        )

        decisions.append(
            ComponentDecision(
                claim=claim,
                status=status,
                evidence=evidence,
                reason=reason,
            )
        )

    return tuple(decisions)
