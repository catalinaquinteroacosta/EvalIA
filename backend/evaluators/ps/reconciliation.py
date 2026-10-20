"""Second pass for blocked PS components only; never coerce ambiguous to a score."""
from dataclasses import dataclass
from .contracts import Decision
from .semantic import SemanticResult

@dataclass(frozen=True)
class ReconciliationSummary:
    results: dict[str, SemanticResult]
    attempted: tuple[str,...]
    unresolved: tuple[str,...]

def reconcile_blocked(initial: dict[str, SemanticResult], retry):
    out=dict(initial)
    attempted=[]
    for code,item in initial.items():
        if item.decision.status!='BLOCKED': continue
        attempted.append(code)
        try:
            updated=retry(code,item)
            if not isinstance(updated,SemanticResult) or updated.indicator!=code:
                raise ValueError('Invalid reconciliation identity')
            out[code]=updated
        except Exception as exc:
            out[code]=SemanticResult(code,Decision(code,None,'BLOCKED',f'Reconciliation failed: {type(exc).__name__}'),item.extracted,item.verified)
    return ReconciliationSummary(out,tuple(attempted),tuple(code for code,item in out.items() if item.decision.status=='BLOCKED'))
