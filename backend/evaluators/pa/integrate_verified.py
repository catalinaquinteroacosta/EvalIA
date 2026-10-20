"""Integra reportes reales de propiedades con controles PA."""

import json
from pathlib import Path

from .contracts import CODES
from .scoring_guard import PropertyRecord
from .applicability_guard import assess_applicability


DIRECTORY = Path("backend/evaluators/pa/reports")

SOURCE = DIRECTORY / "pa_property_audit_20261008_041902.json"
GATE = DIRECTORY / "pa_scoring_gate_20261008_041902.json"
OUTPUT = DIRECTORY / "pa_integrated_20261008_041902.json"


def integrate():
    if OUTPUT.exists():
        raise RuntimeError(
            "El reporte integrado ya existe; no sobrescribir."
        )

    audit = json.loads(SOURCE.read_text(encoding="utf-8-sig"))
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))

    results = {}

    for code in CODES:
        item = audit["results"][code]
        prior = gate["results"][code]

        if item.get("status") != "PENDING_VALIDATION":
            results[code] = {
                "status": "BLOCKED",
                "reason": "Auditoria no disponible",
                "score": None,
            }
            continue

        extracted = item["properties"]
        verified = item["verification"]

        observations = extracted.get("properties", [])
        checks = verified.get("checks", [])

        checks_by_index = {}

        for check in checks:
            index = check.get("property_index")

            if (
                type(index) is not int
                or index in checks_by_index
            ):
                raise ValueError(
                    f"{code}: indice duplicado o invalido"
                )

            checks_by_index[index] = check

        if set(checks_by_index) != set(range(len(observations))):
            raise ValueError(
                f"{code}: cobertura incompleta"
            )

        properties = []

        for index, observation in enumerate(observations):
            quotes = observation.get("quotes", [])

            evidence_valid = (
                isinstance(quotes, list)
                and all(
                    isinstance(q, str) and q
                    for q in quotes
                )
            )

            properties.append(
                PropertyRecord(
                    name=observation.get("name", ""),
                    value=observation.get("value", "uncertain"),
                    verified=(
                        checks_by_index[index].get("status")
                        == "supported"
                    ),
                    evidence_valid=evidence_valid,
                )
            )

        applicability = extracted.get("applicability")
        verified_applicability = verified.get("applicability")

        independent_applicability = (
            applicability == verified_applicability
            and verified.get("coverage") == "complete"
        )

        applicable = {
            "applicable": True,
            "not_applicable": False,
        }.get(applicability)

        result = assess_applicability(
            code=code,
            applicable=applicable,
            independently_verified=independent_applicability,
            reason=extracted.get(
                "applicability_reason", "Sin justificacion"
            ),
            properties=tuple(properties),
            unresolved_discrepancy=(
                prior.get("scoring_gate") == "BLOCKED"
            ),
        )

        results[code] = {
            "status": result.status,
            "reason": result.reason,
            "score": result.score,
            "property_count": len(properties),
            "verified_count": sum(
                p.verified for p in properties
            ),
            "evidence_valid_count": sum(
                p.evidence_valid for p in properties
            ),
        }

    OUTPUT.write_text(
        json.dumps(
            {
                "source": str(SOURCE),
                "gate": str(GATE),
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\n===== PA INTEGRADO =====")

    for code, result in results.items():
        print(
            code,
            result["status"],
            "| verificadas:",
            result.get("verified_count", 0),
            "/",
            result.get("property_count", 0),
        )

    print("\nREPORTE:", OUTPUT)


if __name__ == "__main__":
    integrate()
