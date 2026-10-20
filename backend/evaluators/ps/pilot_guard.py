"""Fail-closed, read-only readiness gate for PS semantic pilot.

Does not replace the official rubric or alter scoring; audits output evidence.
"""
from __future__ import annotations
from dataclasses import dataclass
from .contracts import Turn
from .evidence import verify_literal, EvidenceError
from .semantic import SemanticResult

POSITIVE_ACTION = frozenset({'PS1','PS2','PS3','PS4','PS5','PS9','PS10'})

@dataclass(frozen=True)
class AuditFinding:
    indicator: str
    code: str
    detail: str


def audit_result(turn: Turn, result: SemanticResult) -> tuple[AuditFinding, ...]:
    """Audit a semantic result; no API calls, no changes to scores or files."""
    code = result.indicator
    findings: list[AuditFinding] = []
    def flag(kind, detail):
        findings.append(AuditFinding(code, kind, detail))
    if result.decision.status not in ('SCORED','NA'):
        flag('UNRESOLVED', f'{result.decision.status}: {result.decision.reason}')
        return tuple(findings)
    verified = result.verified
    if not isinstance(verified, dict):
        flag('INVALID_VERIFIER', 'Verifier payload is not an object')
        return tuple(findings)
    if result.decision.status == 'NA':
        if verified.get('applicability', {}).get('predicate') != 'not_applicable':
            flag('NA_UNSUPPORTED', 'No independently verified non-applicability')
        return tuple(findings)
    levels = verified.get('levels', {})
    if not isinstance(levels, dict):
        flag('INVALID_LEVELS', 'Verifier levels must be an object')
        return tuple(findings)
    score = result.decision.score
    selected = levels.get(str(score))
    if not isinstance(selected, dict) or selected.get('verification') != 'supported':
        flag('SCORE_UNSUPPORTED', 'Selected level is not supported by verifier')
        return tuple(findings)
    evidence = selected.get('evidence', [])
    if not isinstance(evidence, list):
        flag('INVALID_EVIDENCE', 'Selected level evidence is not a list')
        return tuple(findings)
    response_quotes = 0
    for raw in evidence:
        try:
            from .contracts import Evidence
            if not isinstance(raw, dict):
                raise EvidenceError('Malformed evidence')
            item = Evidence(source=raw['source'], quote=raw['quote'], history_index=raw.get('history_index'))
            verify_literal(turn, item)
            if item.source == 'response':
                response_quotes += 1
        except (EvidenceError, KeyError, TypeError) as exc:
            flag('INVALID_QUOTE', str(exc))
    if score is not None and score > 0 and code in POSITIVE_ACTION and response_quotes == 0:
        flag('NO_RESPONSE_EVIDENCE', 'Positive action level lacks exact evidence from evaluated response')
    if code in ('PS6','PS7') and score == 3:
        # Negative guardrails can be supported by a full-response absence audit.
        if not verified.get('full_response_audited', False):
            flag('ABSENCE_AUDIT_MISSING', 'Negative guardrail level 3 requires explicit full-response audit flag')
    return tuple(findings)


def audit_family(turn: Turn, results: dict[str, SemanticResult]) -> dict[str, list[dict[str,str]]]:
    return {code: [vars(f) for f in audit_result(turn, result)] for code, result in results.items()}
