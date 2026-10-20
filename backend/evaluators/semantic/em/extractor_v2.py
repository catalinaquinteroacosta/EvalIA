from __future__ import annotations

"""
Extractor EM V2 con trazabilidad temporal exacta.
"""

from typing import Any, Mapping, Sequence

from backend.evaluators.semantic.semantic_provider import (
    run_structured_semantic,
)
from backend.evaluators.semantic.em.schemas import (
    COMPONENT_DESCRIPTIONS,
)
from backend.evaluators.semantic.em.schemas_v2 import (
    get_em_schema_v2,
)
from backend.evaluators.semantic.em.prompts_v2 import (
    build_em_extraction_prompt_v2,
)
from backend.evaluators.semantic.em.evidence_v2 import (
    validate_component_evidence_v2,
)
from backend.evaluators.semantic.em.temporal_context import (
    HistoryMessage,
    normalize_prior_history,
)


EM_EXTRACTOR_V2_VERSION = "EM-EXTRACTOR-2.3.0"

SEMANTIC_VALUES = {"true", "false", "unknown"}


def validate_extraction_structure_v2(
    indicator_code: str,
    result: dict[str, Any],
) -> None:

    code = str(indicator_code).strip().upper()

    if not isinstance(result, dict):
        raise TypeError("La extraccion debe ser dict")

    if result.get("indicator_code") != code:
        raise ValueError(
            "indicator_code no coincide con el solicitado"
        )

    components = result.get("components")

    if not isinstance(components, dict):
        raise TypeError("components debe ser dict")

    expected = set(COMPONENT_DESCRIPTIONS[code])

    if set(components) != expected:
        raise ValueError(
            f"Componentes incorrectos para {code}"
        )

    for name, component in components.items():

        if not isinstance(component, dict):
            raise TypeError(f"{code}.{name} debe ser dict")

        if set(component) != {
            "value",
            "evidence",
            "counterevidence",
            "reason",
        }:
            raise ValueError(
                f"Campos incorrectos en {code}.{name}"
            )

        if component["value"] not in SEMANTIC_VALUES:
            raise ValueError(
                f"Valor invalido en {code}.{name}"
            )

        if not isinstance(component["evidence"], list):
            raise TypeError("evidence debe ser list")

        if not isinstance(component["counterevidence"], list):
            raise TypeError("counterevidence debe ser list")

        if not isinstance(component["reason"], str):
            raise TypeError("reason debe ser str")


def validate_extraction_evidence_v2(
    indicator_code: str,
    result: dict[str, Any],
    *,
    prior_history: Sequence[
        HistoryMessage | Mapping[str, object]
    ] | None = None,
    user_message: str = "",
    ai_response: str = "",
) -> dict[str, dict[str, Any]]:

    validate_extraction_structure_v2(
        indicator_code,
        result,
    )

    validations = {}

    for name, component in result["components"].items():
        validations[name] = validate_component_evidence_v2(
            component,
            prior_history=prior_history,
            user_message=user_message,
            ai_response=ai_response,
        )

    return validations


def extraction_has_literal_errors_v2(
    validations: dict[str, dict[str, Any]],
) -> bool:

    return any(
        not item["evidence_valid"]
        or not item["counterevidence_valid"]
        for item in validations.values()
    )


def extract_em_components_v2(
    *,
    indicator_code: str,
    user_message: str,
    ai_response: str,
    prior_history: Sequence[
        HistoryMessage | Mapping[str, object]
    ] | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:

    code = str(indicator_code).strip().upper()
    history = normalize_prior_history(prior_history)

    prompt = build_em_extraction_prompt_v2(
        indicator_code=code,
        user_message=user_message,
        ai_response=ai_response,
        prior_history=history,
    )


    # Reglas de citacion literal EM.
    # No transforma citas ni modifica valores semanticos.
    prompt += (
        "\n\nEM EXACT QUOTATION DISCIPLINE:\n"
        "When citing numbered or bulleted lists, prefer a "
        "short exact contiguous substring from the item's "
        "content rather than including the list marker. "
        "For example, if the source contains a number followed "
        "by a TAB, do not replace that TAB with a space. "
        "Instead, quote the text beginning immediately after "
        "the TAB, provided it supports the semantic claim. "
        "Copy exact punctuation, accents, whitespace and "
        "capitalization. Never reconstruct or normalize a quote. "
        "Use only literal substrings of the declared source. "
        "Apply these rules to evidence and counterevidence. "
        "Do not change semantic values to accommodate citations. "
        "Do not assign scores.\n"
    )

    schema = get_em_schema_v2(code)

    result = run_structured_semantic(
        prompt=prompt,
        schema=schema,
        provider=provider,
        model=model,
    )

    validate_extraction_structure_v2(code, result)

    validations = validate_extraction_evidence_v2(
        code,
        result,
        prior_history=history,
        user_message=user_message,
        ai_response=ai_response,
    )

    if extraction_has_literal_errors_v2(validations):
        # Report actual rejected references to the semantic extractor.
        # No automatic evidence repair or change to scoring.
        from dataclasses import asdict

        invalid_refs = []
        for name, validation in validations.items():
            for field, checks_name in (
                ("evidence", "evidence_checks"),
                ("counterevidence", "counterevidence_checks"),
            ):
                for check in validation.get(checks_name, []):
                    if check.valid is False:
                        ref = asdict(check.evidence)
                        invalid_refs.append({
                            "component": name,
                            "field": field,
                            "source": ref.get("source"),
                            "history_index": ref.get("history_index"),
                            "quote": ref.get("quote"),
                            "error": check.error,
                        })

        import json
        details = json.dumps(
            invalid_refs, ensure_ascii=False, indent=2,
        )
        retry_prompt = prompt + (
            "\n\nCONTROLLED LITERAL EXTRACTION RETRY.\n"
            "The following references failed exact-source validation:\n"
            + details
            + "\nProduce a NEW independent semantic extraction for "
              "every component; do not merely patch the old JSON. "
              "The errors above are evidence-validation failures, "
              "not instructions to change semantic values. "
              "Use only the supplied current user, response and "
              "ordered prior history. For each quote, copy a "
              "CONTIGUOUS exact substring character for character "
              "from its declared source, including tabs, spaces, "
              "accents and punctuation. Do not paraphrase or "
              "silently change source or history_index. "
              "If evidence comes from the current user, declare "
              "source=user, never response. For response citations, "
              "quote the response itself, not a user's sentence "
              "that the response merely discusses. "
              "For numbered lists, omit the list marker and "
              "copy an exact substring of the item content. "
              "Never replace TAB characters with spaces. "
              "Do not normalize any quotation. "
              "If a valid quote is unavailable, do not invent one. "
              "Do not assign any score. Return the required JSON."
        )

        result = run_structured_semantic(
            prompt=retry_prompt,
            schema=schema,
            provider=provider,
            model=model,
        )

        validate_extraction_structure_v2(
            code,
            result,
        )

        validations = validate_extraction_evidence_v2(
            code,
            result,
            prior_history=history,
            user_message=user_message,
            ai_response=ai_response,
        )


    if extraction_has_literal_errors_v2(validations):
        # Ultimo intento semantico independiente.
        # Nunca modifica automaticamente las citas.
        from dataclasses import asdict

        rejected = []

        for name, validation in validations.items():
            for field, checks_name in (
                ("evidence", "evidence_checks"),
                ("counterevidence", "counterevidence_checks"),
            ):
                for check in validation.get(checks_name, []):
                    if check.valid is False:
                        rejected.append({
                            "component": name,
                            "field": field,
                            "reference": asdict(check.evidence),
                            "error": check.error,
                        })

        import json

        final_prompt = prompt + (
            "\n\nFINAL INDEPENDENT LITERAL EXTRACTION.\n"
            "The previous attempts contained these invalid "
            "source quotations:\n"
            + json.dumps(
                rejected,
                ensure_ascii=False,
                indent=2,
            )
            + "\nReassess every component independently. "
              "Preserve the original semantic definitions. "
              "Use short verbatim contiguous substrings "
              "copied from the declared source. "
              "For numbered lists, omit the number and "
              "its following whitespace; quote only "
              "the exact item content. "
              "Never paraphrase, reconstruct, normalize, "
              "or invent evidence. "
              "If literal evidence is unavailable, "
              "do not fabricate a quotation. "
              "Do not assign scores. "
              "Return the required JSON."
        )

        result = run_structured_semantic(
            prompt=final_prompt,
            schema=schema,
            provider=provider,
            model=model,
        )

        validate_extraction_structure_v2(
            code,
            result,
        )

        validations = validate_extraction_evidence_v2(
            code,
            result,
            prior_history=history,
            user_message=user_message,
            ai_response=ai_response,
        )

    if extraction_has_literal_errors_v2(validations):
        failures = []

        for name, validation in validations.items():
            for field, checks_name in (
                ("evidence", "evidence_checks"),
                ("counterevidence", "counterevidence_checks"),
            ):
                for check in validation.get(checks_name, []):
                    if check.valid is False:
                        from dataclasses import asdict

                        ref = asdict(check.evidence)
                        failures.append({
                            "component": name,
                            "field": field,
                            "source": ref.get("source"),
                            "history_index": ref.get("history_index"),
                            "quote": ref.get("quote"),
                            "error": check.error,
                        })

        raise ValueError(
            "Extractor con evidencia literal inv?lida "
            "tras reintento: "
            + repr(failures)
        )

    return {
        "indicator_code": code,
        "components": result["components"],
        "literal_evidence_valid": (
            not extraction_has_literal_errors_v2(
                validations
            )
        ),
        "evidence_validation": validations,
        "extractor_version": EM_EXTRACTOR_V2_VERSION,
    }
