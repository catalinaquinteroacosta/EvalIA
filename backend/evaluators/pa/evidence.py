from .contracts import Turn, Evidence

def exact_quote(turn: Turn, evidence: Evidence) -> bool:
    if not evidence.quote: return False
    if evidence.source == 'history':
        i=evidence.history_index
        return type(i) is int and 0 <= i < len(turn.prior_history) and evidence.quote in turn.prior_history[i].text
    if evidence.history_index is not None: return False
    if evidence.source == 'user': return evidence.quote in turn.user
    if evidence.source == 'response': return evidence.quote in turn.response
    return False

def validate_evidence(turn: Turn, evidences: tuple[Evidence,...]):
    for e in evidences:
        if not exact_quote(turn,e):
            raise ValueError(f'Nonliteral or incorrectly attributed evidence: {e!r}')
