from __future__ import annotations

"""
Extractor semantico EM1-EM13.

Responsabilidad:
- construir el prompt del indicador;
- ejecutar extraccion estructurada mediante semantic_provider;
- validar estructura basica del resultado;
- validar literalidad de evidence/counterevidence;
- devolver componentes extraidos con trazabilidad.

NO:
- asigna 0/1/2/3;
- decide aplicabilidad final;
- verifica semanticamente sus propias afirmaciones;
- modifica citas;
- usa regex para interpretar lenguaje.
"""

from typing import Any

from backend.evaluators.semantic.semantic_provider import (
    run_structured_semantic,
)
from backend.evaluators.semantic.em.schemas import (
    COMPONENT_DESCRIPTIONS,
    get_em_schema,
)
from backend.evaluators.semantic.em.prompts import (
    build_em_extraction_prompt,
)
from backend.evaluators.semantic.em.evidence import (
    validate_component_evidence,
)


EM_EXTRACTOR_VERSION = "EM-EXTRACTOR-1.1.0"

SEMANTIC_VALUES = {
    "true",
    "false",
    "unknown",
}


def validate_extraction_structure(
    indicator_code: str,
    result: dict[str, Any],
) -> None:
    code = str(indicator_code).strip().upper()

    if not isinstance(result, dict):
        raise TypeError("La extraccion EM debe ser dict")

    if result.get("indicator_code") != code:
        raise ValueError(
            "indicator_code de extraccion no coincide con el solicitado"
        )

    components = result.get("components")

    if not isinstance(components, dict):
        raise TypeError("result['components'] debe ser dict")

    expected = set(COMPONENT_DESCRIPTIONS[code])
    actual = set(components)

    if actual != expected:
        raise ValueError(
            f"Componentes incorrectos para {code}: "
            f"actual={sorted(actual)!r}, "
            f"expected={sorted(expected)!r}"
        )

    for name, component in components.items():
        if not isinstance(component, dict):
            raise TypeError(
                f"{code}.{name} debe ser dict"
            )

        expected_fields = {
            "value",
            "evidence",
            "counterevidence",
            "reason",
        }

        if set(component) != expected_fields:
            raise ValueError(
                f"Campos incorrectos en {code}.{name}: "
                f"{sorted(component)!r}"
            )

        if component["value"] not in SEMANTIC_VALUES:
            raise ValueError(
                f"Valor invalido en {code}.{name}: "
                f"{component['value']!r}"
            )

        if not isinstance(component["evidence"], list):
            raise TypeError(
                f"{code}.{name}.evidence debe ser list"
            )

        if not isinstance(component["counterevidence"], list):
            raise TypeError(
                f"{code}.{name}.counterevidence debe ser list"
            )

        if not isinstance(component["reason"], str):
            raise TypeError(
                f"{code}.{name}.reason debe ser str"
            )


def validate_extraction_evidence(
    indicator_code: str,
    result: dict[str, Any],
    *,
    previous_context: str = "",
    user_message: str = "",
    ai_response: str = "",
) -> dict[str, dict[str, Any]]:
    """
    Valida literalidad de todas las citas producidas por el extractor.

    No valida todavia si la cita demuestra semanticamente el claim.
    """

    validate_extraction_structure(
        indicator_code,
        result,
    )

    validations: dict[str, dict[str, Any]] = {}

    for name, component in result["components"].items():
        validations[name] = validate_component_evidence(
            component,
            previous_context=previous_context,
            user_message=user_message,
            ai_response=ai_response,
        )

    return validations


def extraction_has_literal_evidence_errors(
    validations: dict[str, dict[str, Any]],
) -> bool:
    for validation in validations.values():
        if not validation["evidence_valid"]:
            return True

        if not validation["counterevidence_valid"]:
            return True

    return False


def extract_em_components(
    *,
    indicator_code: str,
    user_message: str,
    ai_response: str,
    previous_context: str = "",
    provider: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Ejecuta extraccion semantica de UN indicador EM.

    El resultado todavia NO esta semanticamente verificado y NO contiene
    puntuacion.
    """

    code = str(indicator_code).strip().upper()

    schema = get_em_schema(code)

    prompt = build_em_extraction_prompt(
        indicator_code=code,
        user_message=user_message,
        ai_response=ai_response,
        previous_context=previous_context,
    )

    result = run_structured_semantic(
        prompt=prompt,
        schema=schema,
        provider=provider,
        model=model,
    )

    validate_extraction_structure(
        code,
        result,
    )

    validations = validate_extraction_evidence(
        code,
        result,
        previous_context=previous_context,
        user_message=user_message,
        ai_response=ai_response,
    )

    return {
        "indicator_code": code,
        "components": result["components"],
        "literal_evidence_valid": (
            not extraction_has_literal_evidence_errors(validations)
        ),
        "evidence_validation": validations,
        "extractor_version": EM_EXTRACTOR_VERSION,
    }
