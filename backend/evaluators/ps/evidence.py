from .contracts import Evidence, Turn

class EvidenceError(ValueError):
    pass

def source_text(turn: Turn, item: Evidence) -> str:
    if item.source == 'history':
        i = item.history_index
        if type(i) is not int or i < 0 or i >= len(turn.prior_history):
            raise EvidenceError('Invalid history_index')
        msg = turn.prior_history[i]
        if msg.role not in ('user', 'assistant'):
            raise EvidenceError('Invalid history role')
        return msg.text
    if item.history_index is not None:
        raise EvidenceError('history_index must be null for current messages')
    if item.source == 'user':
        return turn.user
    if item.source == 'response':
        return turn.response
    raise EvidenceError('Invalid source')

def verify_literal(turn: Turn, item: Evidence) -> bool:
    if not item.quote or item.quote not in source_text(turn, item):
        raise EvidenceError('Quote not exactly present in declared source')
    return True
