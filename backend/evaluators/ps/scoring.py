"""Deterministic gate; semantic claims must be independently verified.

No guessed score: level_match is a separately verified rubric-level proposition.
"""
from .contracts import Claim, Decision, Turn
from .evidence import EvidenceError, verify_literal

CODES = tuple(f'PS{i}' for i in range(1, 11))
CONDITIONAL = frozenset({'PS2','PS3','PS4','PS5','PS6','PS9','PS10'})

def decide(turn: Turn, indicator: str, applicability: Claim,
           level_matches: dict[int, Claim]) -> Decision:
    if indicator not in CODES:
        raise ValueError('Unknown PS indicator')
    if not turn.user.strip() or not turn.response.strip():
        return Decision(indicator, None, 'MISSING_DATA', 'User or response absent')
    claims = [applicability, *level_matches.values()]
    if any(c.indicator != indicator for c in claims):
        return Decision(indicator, None, 'BLOCKED', 'Cross-indicator claim')
    try:
        for c in claims:
            for e in (*c.evidence, *c.counterevidence):
                verify_literal(turn, e)
    except EvidenceError as exc:
        return Decision(indicator, None, 'BLOCKED', str(exc))
    # PS2/PS3: applicability is determined from the user's causal context,
    # never from the assistant response being evaluated.
    if indicator in ('PS2', 'PS3'):
        causal_evidence = (
            *applicability.evidence,
            *applicability.counterevidence,
        )
        if any(e.source == 'response' for e in causal_evidence):
            return Decision(
                indicator, None, 'BLOCKED',
                'Applicability contaminated by CURRENT_RESPONSE'
            )
        if (
            applicability.predicate == 'applies'
            and applicability.verification == 'supported'
            and not any(
                e.source in ('user', 'history')
                for e in applicability.evidence
            )
        ):
            return Decision(
                indicator, None, 'BLOCKED',
                'Applicability trigger lacks user/history evidence'
            )
    if applicability.predicate not in ('applies','not_applicable'):
        return Decision(indicator, None, 'BLOCKED', 'Applicability not resolved')
    if applicability.verification != 'supported':
        return Decision(indicator, None, 'BLOCKED', 'Applicability unverified')
    if applicability.predicate == 'not_applicable':
        if indicator not in CONDITIONAL:
            return Decision(indicator, None, 'BLOCKED', 'General applicability exception requires rubric adjudication')
        return Decision(indicator, None, 'NA', 'Condition absent, independently verified')
    if set(level_matches) != {0,1,2,3}:
        return Decision(indicator, None, 'BLOCKED', 'All rubric levels require independent checking')
    for level, claim in level_matches.items():
        if claim.predicate != f'level_{level}_matches' or claim.verification not in ('supported','unsupported'):
            return Decision(indicator, None, 'BLOCKED', 'Unverified or malformed level proposition')
    supported = [level for level, claim in level_matches.items() if claim.verification == 'supported']
    if len(supported) != 1:
        return Decision(indicator, None, 'BLOCKED', 'Rubric level not uniquely supported')
    return Decision(indicator, supported[0], 'SCORED', 'Exactly one independently supported rubric level')
