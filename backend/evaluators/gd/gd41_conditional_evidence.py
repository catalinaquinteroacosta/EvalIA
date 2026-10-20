
import json
from datetime import datetime
from pathlib import Path

from backend.evaluators.gd.gd_schemas import (
    GDContext,
    Evidence,
    verify_exact_quote,
)
from backend.evaluators.semantic.semantic_provider import (
    run_structured_semantic,
)

ROOT = Path("backend/evaluators/gd")
SOURCE = ROOT / "reports/contrasts/GD_AUTONOMIA_NEGADA.json"
AUDITS = ROOT / "reports/audits"

CODES = ("GD5", "GD7")

ITEM_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "code": {
            "type": "string",
            "enum": list(CODES),
        },
        "condition": {
            "type": "string",
            "enum": ["yes", "no", "uncertain"],
        },
        "reason": {"type": "string"},
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "quote": {"type": "string"},
                    "source": {
                        "type": "string",
                        "enum": [
                            "CURRENT_USER",
                            "CURRENT_RESPONSE",
                            "PRIOR_HISTORY",
                        ],
                    },
                    "history_index": {
                        "type": ["integer", "null"],
                    },
                },
                "required": [
                    "quote",
                    "source",
                    "history_index",
                ],
            },
        },
    },
    "required": [
        "code",
        "condition",
        "reason",
        "evidence",
    ],
}

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "items": {
            "type": "array",
            "items": ITEM_SCHEMA,
        },
    },
    "required": ["items"],
}

VERIFY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "code": {
                        "type": "string",
                        "enum": list(CODES),
                    },
                    "verdict": {
                        "type": "string",
                        "enum": [
                            "supported",
                            "not_supported",
                            "ambiguous",
                        ],
                    },
                    "reason": {"type": "string"},
                },
                "required": [
                    "code",
                    "verdict",
                    "reason",
                ],
            },
        },
    },
    "required": ["items"],
}


def validate_items(raw, context):
    if not isinstance(raw, dict):
        raise ValueError("Extracci?n inv?lida.")

    items = raw.get("items")
    if not isinstance(items, list):
        raise ValueError("Faltan condiciones.")

    codes = [item.get("code") for item in items]

    if len(codes) != 2 or set(codes) != set(CODES):
        raise ValueError("Se requieren GD5 y GD7 ?nicos.")

    for item in items:
        if item.get("condition") not in (
            "yes", "no", "uncertain"
        ):
            raise ValueError("Condici?n inv?lida.")

        if not isinstance(item.get("reason"), str):
            raise ValueError("Justificaci?n inv?lida.")

        evidence = item.get("evidence")
        if not isinstance(evidence, list):
            raise ValueError("Evidencia inv?lida.")

        for entry in evidence:
            evidence_object = Evidence(**entry)
            if not verify_exact_quote(
                evidence_object,
                context,
            ):
                raise ValueError(
                    "Cita activadora no literal."
                )

        if item["condition"] == "yes" and not evidence:
            raise ValueError(
                "Condici?n afirmativa sin se?al literal."
            )

    return items


def validate_verification(raw):
    if not isinstance(raw, dict):
        raise ValueError("Verificaci?n inv?lida.")

    items = raw.get("items")
    if not isinstance(items, list):
        raise ValueError("Faltan verificaciones.")

    codes = [item.get("code") for item in items]

    if len(codes) != 2 or set(codes) != set(CODES):
        raise ValueError("Cobertura inv?lida.")

    for item in items:
        if item.get("verdict") not in (
            "supported",
            "not_supported",
            "ambiguous",
        ):
            raise ValueError("Veredicto inv?lido.")

        if not isinstance(item.get("reason"), str):
            raise ValueError("Motivo inv?lido.")

    return items


def main():
    data = json.loads(
        SOURCE.read_text(encoding="utf-8-sig")
    )

    context = GDContext(**data["context"])

    prompt = (
        "Extract conditional applicability for GD5 and GD7 "
        "WITHOUT scoring. "
        "GD5 official condition: independent sources, "
        "professionals, tools or relationships are relevant "
        "in this context. "
        "GD7 official condition: a functional limitation "
        "must be explained or a human/professional role "
        "attribution must be corrected. "
        "For each code return yes, no or uncertain. "
        "When yes, cite exact contextual activation signals. "
        "Citations must be literal substrings, with correct "
        "source and zero-based history_index when applicable. "
        "Do not invent a condition or treat omitted behavior "
        "as proof of non-applicability. "
        "Do not use future turns. "
        "Context:\n"
        + json.dumps(data["context"], ensure_ascii=False)
    )

    print("GD-41 | EXTRACCI?N CONDICIONAL", flush=True)

    extraction = run_structured_semantic(
        prompt=prompt,
        schema=SCHEMA,
        provider="openai",
        max_output_tokens=2000,
    )

    try:
        extracted = validate_items(extraction, context)
    except (ValueError, TypeError, KeyError) as first_error:
        print(
            "GD-41 | EXTRACCI?N INV?LIDA:",
            str(first_error),
            flush=True,
        )
        print(
            "GD-41 | COBERTURA RECIBIDA:",
            [
                item.get("code")
                for item in extraction.get("items", [])
                if isinstance(item, dict)
            ] if isinstance(extraction, dict) else "NO_DICT",
            flush=True,
        )

        repair_prompt = (
            prompt
            + "\\nREPAIR: The previous response failed "
              "strict validation. Return EXACTLY two items: "
              "GD5 and GD7, once each. Do not include other "
              "indicators. Preserve only literal evidence. "
              "Do not invent citations. If applicability "
              "cannot be established, return uncertain. "
            + "\\nValidation error: "
            + str(first_error)
            + "\\nPrevious invalid response: "
            + json.dumps(extraction, ensure_ascii=False)
        )

        extraction = run_structured_semantic(
            prompt=repair_prompt,
            schema=SCHEMA,
            provider="openai",
            max_output_tokens=2000,
        )

        extracted = validate_items(extraction, context)

    verification_prompt = (
        "Independently verify whether each GD5/GD7 "
        "applicability conclusion is semantically supported "
        "by the ORIGINAL CONTEXT and exact cited evidence. "
        "Do not assume the extractor is correct. "
        "Do not score. "
        "supported means the claimed condition is correct; "
        "not_supported means contradicted; "
        "ambiguous means unresolved. "
        "A literal citation alone does not prove relevance. "
        "Do not add criteria beyond the official conditions. "
        "Context:\n"
        + json.dumps(data["context"], ensure_ascii=False)
        + "\nExtraction:\n"
        + json.dumps(extraction, ensure_ascii=False)
    )

    print("GD-41 | VERIFICACI?N INDEPENDIENTE", flush=True)

    verification = run_structured_semantic(
        prompt=verification_prompt,
        schema=VERIFY_SCHEMA,
        provider="openai",
        max_output_tokens=1500,
    )

    verified = validate_verification(verification)

    by_code = {
        item["code"]: item
        for item in extracted
    }

    results = {}

    for item in verified:
        code = item["code"]
        condition = by_code[code]["condition"]

        if item["verdict"] != "supported":
            status = "BLOCKED"
        elif condition == "yes":
            status = "APPLICABLE"
        elif condition == "no":
            status = "NA"
        else:
            status = "BLOCKED"

        results[code] = {
            "status": status,
            "condition": condition,
            "verification": item,
            "activation_evidence":
                by_code[code]["evidence"],
        }

    AUDITS.mkdir(parents=True, exist_ok=True)
    destination = AUDITS / (
        "GD41_CONDITIONS_"
        + datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        + ".json"
    )

    destination.write_text(
        json.dumps(
            {
                "source": str(SOURCE),
                "extraction": extraction,
                "verification": verification,
                "results": results,
                "scores_modified": False,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    for code in CODES:
        item = results[code]
        print(
            code,
            item["status"],
            "CONDICI?N:",
            item["condition"],
            "CITAS:",
            len(item["activation_evidence"]),
        )
        print(
            "VERIFICADOR:",
            item["verification"]["reason"],
        )

    print("AUDITOR?A:", destination)
    print("PUNTUACIONES MODIFICADAS: 0")
    print("OTRAS FAMILIAS: SIN MODIFICACIONES")


if __name__ == "__main__":
    main()
