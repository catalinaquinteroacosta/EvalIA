
"""Contrato de verificaci?n por afirmaci?n para GD5-GD7."""

from dataclasses import dataclass

CODES = ("GD5", "GD6", "GD7")
VERDICTS = ("supported", "not_supported", "ambiguous")


@dataclass(frozen=True)
class Claim:
    code: str
    claim_id: str
    proposition: str


@dataclass(frozen=True)
class ClaimVerdict:
    code: str
    claim_id: str
    verdict: str
    reason: str


def validate_claims(claims):
    if not isinstance(claims, (list, tuple)):
        raise ValueError("Afirmaciones inv?lidas.")

    if not claims:
        raise ValueError("No hay afirmaciones.")

    seen = set()

    for claim in claims:
        if not isinstance(claim, Claim):
            raise TypeError("Claim inv?lido.")

        if claim.code not in CODES:
            raise ValueError("Indicador fuera de alcance.")

        if not claim.claim_id.strip():
            raise ValueError("Identificador vac?o.")

        if not claim.proposition.strip():
            raise ValueError("Proposici?n vac?a.")

        key = (claim.code, claim.claim_id)

        if key in seen:
            raise ValueError("Afirmaci?n duplicada.")

        seen.add(key)

    return tuple(claims)


def validate_verdicts(claims, verdicts):
    claims = validate_claims(claims)

    if not isinstance(verdicts, (list, tuple)):
        raise ValueError("Veredictos inv?lidos.")

    expected = {
        (claim.code, claim.claim_id)
        for claim in claims
    }

    actual = set()

    for verdict in verdicts:
        if not isinstance(verdict, ClaimVerdict):
            raise TypeError("ClaimVerdict inv?lido.")

        key = (verdict.code, verdict.claim_id)

        if key not in expected:
            raise ValueError("Veredicto no solicitado.")

        if key in actual:
            raise ValueError("Veredicto duplicado.")

        if verdict.verdict not in VERDICTS:
            raise ValueError("Estado inv?lido.")

        if not verdict.reason.strip():
            raise ValueError("Motivo vac?o.")

        actual.add(key)

    if actual != expected:
        raise ValueError("Faltan verificaciones.")

    return tuple(verdicts)


def summarize_claims(claims, verdicts):
    validated = validate_verdicts(claims, verdicts)

    grouped = {}

    for item in validated:
        grouped.setdefault(item.code, []).append(item)

    result = {}

    for code, items in grouped.items():
        result[code] = (
            "VERIFIED"
            if all(
                item.verdict == "supported"
                for item in items
            )
            else "BLOCKED"
        )

    return result
