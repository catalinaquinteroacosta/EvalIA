"""Extraccion y verificacion semantica ND por indicador."""

from dataclasses import dataclass

from .contracts import ND_CODES, TurnContext
from .official_rubric import load_official_nd_rubric


@dataclass(frozen=True)
class VerifiedIndicatorComponent:
    claim: str
    evidence: tuple[dict, ...]
    verdict: str
    reason: str


@dataclass(frozen=True)
class IndicatorSemanticReport:
    indicator: str
    official_question: str
    status: str
    components: tuple[VerifiedIndicatorComponent, ...]
    reason: str


def assess_indicator_semantics(
    engine,
    indicator: str,
    context: TurnContext,
) -> IndicatorSemanticReport:
    rubric = load_official_nd_rubric()

    if indicator not in ND_CODES:
        raise ValueError("Indicador ND invalido")

    question = rubric.indicators[indicator]["question"]

    extracted = engine.extract(indicator, context)
    components = extracted.get("components")

    if not isinstance(components, list):
        raise ValueError("Extraccion sin componentes validos")

    verified = []

    for component in components:
        claim = component["claim"]
        evidence = component["evidence"]

        if not evidence:
            raise ValueError("Componente sin evidencia")

        for item in evidence:
            source = item.get("source")
            quote = item.get("quote")

            if not isinstance(quote, str) or not quote:
                raise ValueError("Cita vacia")

            if source == "response":
                original = context.response
            elif source == "user":
                original = context.user
            elif source == "history":
                index = item.get("history_index")
                if type(index) is not int:
                    raise ValueError("Indice historico invalido")
                if not 0 <= index < len(context.prior_history):
                    raise ValueError("Indice historico fuera de rango")
                original = context.prior_history[index].text
            else:
                raise ValueError("Fuente de evidencia invalida")

            if quote not in original:
                raise ValueError("Evidencia no literal")

        result = engine.verify(indicator, context, component)

        verified.append(
            VerifiedIndicatorComponent(
                claim=claim,
                evidence=tuple(evidence),
                verdict=result["verdict"],
                reason=result["reason"],
            )
        )

    if not verified:
        status = "BLOCKED"
        reason = "Sin componentes verificables"
    elif any(
        item.verdict != "supported"
        for item in verified
    ):
        status = "BLOCKED"
        reason = "Hay afirmaciones sin soporte independiente"
    else:
        status = "VERIFIED"
        reason = "Componentes con evidencia literal verificada"

    return IndicatorSemanticReport(
        indicator=indicator,
        official_question=question,
        status=status,
        components=tuple(verified),
        reason=reason,
    )
