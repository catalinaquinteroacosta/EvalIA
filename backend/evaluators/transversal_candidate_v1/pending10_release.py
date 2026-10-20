"""Next isolated revision after documented batch-02 entailment defects."""
from copy import copy
from .pending10_final import final_definitions as previous_definitions,CHANGED
from .pending10_ni6_precision import ni6_precision_definitions
from .pending10_contextual_entailment import contextual_entailment_definitions
from .pending10_ri2 import ri2_definitions
from .crisis import CrisisEvaluator as Protocol

VERSION='CRISIS-PENDING10-RELEASE-20261014-2'
CHANGED=CHANGED|{'CR-RI2'}
def final_definitions(definitions):
    return ri2_definitions(contextual_entailment_definitions(ni6_precision_definitions(previous_definitions(definitions))))
class CrisisEvaluator(Protocol):
    def _pair(self,context,definitions,candidates=None,recovery=False):
        updated=final_definitions(definitions)
        original=self.provider;seed=getattr(original,'seed',None)
        if isinstance(seed,dict) and any(k.split('.',1)[0] in CHANGED for k in seed):
            isolated=copy(original)
            isolated.seed={k:v for k,v in seed.items() if k.split('.',1)[0] not in CHANGED}
            self.provider=isolated
        try:return super()._pair(context,updated,candidates,recovery)
        finally:self.provider=original
