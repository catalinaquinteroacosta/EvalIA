"""Orquestación aislada GD: verificar, bloquear y reconciliar.

No puntúa. Nunca convierte incertidumbre en 0 ni en N/A.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .gd_rubric import GD_RUBRIC
from .gd_schemas import GDContext
from .gd_extractor import extract_gd, validate_extraction
from .gd_verifier import verify_gd, validate_verification


@dataclass(frozen=True)
class GDDecision:
    code: str
    status: str
    reason: str
    components: tuple[dict[str, Any], ...]
    verdicts: tuple[dict[str, Any], ...]
    condition_present: str


def assess_verified(
    extraction: dict[str, Any],
    verification: dict[str, Any],
) -> dict[str, GDDecision]:
    """Primera pasada: aísla solo indicadores no verificables."""

    validate_verification(verification, extraction)

    verdict_map = {
        (v["code"], v["component_index"]): v
        for v in verification["verdicts"]
    }

    output = {}

    for item in extraction["indicators"]:
        code = item["code"]
        components = item["components"]
        verdicts = tuple(
            verdict_map[(code, i)]
            for i in range(len(components))
        )

        condition = item["condition_present"]

        issues = [
            f"componente {v['component_index']}: {v['verdict']}"
            for v in verdicts
            if v["verdict"] != "supported"
        ]

        if condition == "uncertain":
            issues.append("aplicabilidad incierta")

        if issues:
            status = "BLOCKED"
            reason = "; ".join(issues)
        elif code in ("GD5", "GD7") and condition == "no":
            status = "NA_CANDIDATE"
            reason = "Condición declarada ausente; requiere validación independiente."
        else:
            status = "VERIFIED"
            reason = "Componentes verificados; puntuación aún pendiente."

        output[code] = GDDecision(
            code=code,
            status=status,
            reason=reason,
            components=tuple(components),
            verdicts=verdicts,
            condition_present=condition,
        )

    return output


def run_gd_first_pass(
    context: GDContext,
    *,
    provider: str = "openai",
    model: str | None = None,
    use_cache: bool = True,
) -> dict[str, GDDecision]:
    """Extrae y verifica. Un fallo técnico nunca produce un puntaje."""

    extraction = extract_gd(
        context,
        provider=provider,
        model=model,
        use_cache=use_cache,
    )
    extraction = validate_extraction(extraction, context)

    verification = verify_gd(
        context,
        extraction,
        provider=provider,
        model=model,
        use_cache=use_cache,
    )

    return assess_verified(extraction, verification)


def reconcile_blocked(
    first_pass: dict[str, GDDecision],
    resolver: Callable[[GDDecision], GDDecision],
) -> dict[str, GDDecision]:
    """Segunda pasada exclusivamente sobre indicadores BLOCKED.

    El resolver deberá implementar una reconciliación semántica
    independiente y comprobable. No se desbloquea por defecto.
    """

    if set(first_pass) != set(GD_RUBRIC):
        raise ValueError("La primera pasada debe cubrir GD1-GD8.")

    output = dict(first_pass)

    for code, original in first_pass.items():
        if original.status != "BLOCKED":
            continue

        candidate = resolver(original)

        if not isinstance(candidate, GDDecision):
            raise TypeError("El resolver debe devolver GDDecision.")

        if candidate.code != code:
            raise ValueError("La reconciliación cambió el indicador.")

        if candidate.status not in (
            "BLOCKED",
            "VERIFIED",
            "NA_CANDIDATE",
        ):
            raise ValueError("Estado de reconciliación inválido.")

        if candidate.status != "BLOCKED":
            if candidate.condition_present == "uncertain":
                raise ValueError("Aplicabilidad sin resolver.")

            if any(
                v["verdict"] != "supported"
                for v in candidate.verdicts
            ):
                raise ValueError(
                    "No se puede desbloquear evidencia no verificada."
                )

            if candidate.status == "NA_CANDIDATE" and not (
                code in ("GD5", "GD7")
                and candidate.condition_present == "no"
            ):
                raise ValueError("N/A incompatible con el indicador.")

        output[code] = candidate

    return output
