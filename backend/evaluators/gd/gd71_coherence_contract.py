"""Contrato conservador de coherencia GD5-GD7.

No punt?a ni sustituye la r?brica oficial.
No convierte discrepancias en resultados favorables.
"""

from __future__ import annotations

from typing import Any


FOCUS = frozenset({"GD5", "GD6", "GD7"})


def audit_coherence(
    extraction: dict[str, Any],
    component_verification: dict[str, Any],
    classification: dict[str, Any],
    level_verification: dict[str, Any],
    applicability: dict[str, str],
) -> dict[str, dict[str, Any]]:
    extracted = {
        item["code"]: item
        for item in extraction["indicators"]
    }
    levels = {
        item["code"]: item
        for item in classification["indicators"]
    }
    component_checks = {}
    for item in component_verification["verdicts"]:
        component_checks.setdefault(
            item["code"], []
        ).append(item)

    level_checks = {
        item["code"]: item
        for item in level_verification["verdicts"]
    }

    output = {}

    for code in sorted(FOCUS):
        issues = []

        if code not in extracted or code not in levels:
            issues.append("MISSING_INDICATOR")
        elif code not in level_checks:
            issues.append("MISSING_LEVEL_VERIFICATION")
        else:
            components = extracted[code]["components"]
            checks = component_checks.get(code, [])

            expected_indices = set(range(len(components)))
            actual_indices = {
                item["component_index"]
                for item in checks
            }

            if actual_indices != expected_indices:
                issues.append("INCOMPLETE_COMPONENT_COVERAGE")

            if any(
                item["verdict"] != "supported"
                for item in checks
            ):
                issues.append(
                    "UNRESOLVED_COMPONENT_DISAGREEMENT"
                )

            if level_checks[code]["verdict"] != "supported":
                issues.append(
                    "UNRESOLVED_LEVEL_DISAGREEMENT"
                )

            if code in ("GD5", "GD7"):
                if applicability.get(code) == "BLOCKED":
                    issues.append(
                        "UNRESOLVED_APPLICABILITY"
                    )
                elif applicability.get(code) not in (
                    "APPLICABLE", "NA"
                ):
                    issues.append(
                        "INVALID_APPLICABILITY"
                    )

            if code == "GD6":
                if any(
                    item["verdict"] == "not_supported"
                    for item in checks
                ):
                    issues.append(
                        "GD6_CLAIM_REQUIRES_RECONCILIATION"
                    )

            if code == "GD7":
                if any(
                    item["verdict"] == "not_supported"
                    for item in checks
                ):
                    issues.append(
                        "GD7_ROLE_CLAIM_REQUIRES_RECONCILIATION"
                    )

        output[code] = {
            "status": (
                "BLOCKED" if issues else "CONSISTENT"
            ),
            "issues": sorted(set(issues)),
            "score": None,
        }

    return output
