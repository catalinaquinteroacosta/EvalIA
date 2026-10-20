"""Determina si la auditoria compartida autoriza CE1.

Una omision exclusiva de CE2 no bloquea CE1.
Una auditoria ambigua nunca se aprueba.
"""

CE1_FIELDS = {
    "primary_need",
    "explicit_needs",
    "contextual_needs",
    "ce1_relevant_evidence",
    "ce1_digressions",
}

CE2_FIELDS = {
    "ce2_essential_information_present",
    "ce2_essential_omissions",
    "ce2_unnecessary_overload",
}


def assess_ce1_coverage(audit):
    if (
        not isinstance(audit, dict)
        or set(audit) != {
            "verdict", "findings", "reason"
        }
        or audit["verdict"] not in {
            "complete", "incomplete", "ambiguous"
        }
        or not isinstance(audit["findings"], list)
        or not isinstance(audit["reason"], str)
        or not audit["reason"].strip()
    ):
        raise ValueError(
            "Auditoria de cobertura invalida."
        )

    findings = audit["findings"]
    allowed = CE1_FIELDS | CE2_FIELDS

    for item in findings:
        if (
            not isinstance(item, dict)
            or set(item) != {
                "field", "issue", "evidence"
            }
            or item["field"] not in allowed
            or not isinstance(item["issue"], str)
            or not item["issue"].strip()
            or not isinstance(item["evidence"], str)
        ):
            raise ValueError(
                "Hallazgo de cobertura invalido."
            )

    if audit["verdict"] == "complete" and findings:
        raise ValueError(
            "Cobertura completa con hallazgos."
        )

    if (
        audit["verdict"] == "incomplete"
        and not findings
    ):
        raise ValueError(
            "Cobertura incompleta sin hallazgos."
        )

    ce1 = [
        item for item in findings
        if item["field"] in CE1_FIELDS
    ]
    ce2 = [
        item for item in findings
        if item["field"] in CE2_FIELDS
    ]

    if audit["verdict"] == "ambiguous":
        status = "ambiguous"
        approved = False
    elif ce1:
        status = "incomplete"
        approved = False
    else:
        status = "complete"
        approved = True

    return {
        "status": status,
        "approved": approved,
        "ce1_findings": ce1,
        "ce2_findings": ce2,
        "shared_audit_verdict": audit["verdict"],
        "reason": audit["reason"],
    }
