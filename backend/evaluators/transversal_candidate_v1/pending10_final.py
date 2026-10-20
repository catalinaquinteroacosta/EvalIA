"""Explicit isolated ten-indicator composition; frozen/visual routes unchanged."""
from copy import copy
from .crisis import CrisisEvaluator as Protocol
from .pending10_contextual import contextual_definitions
from .pending10_ri3 import ri3_definitions
from .pending10_ni6 import ni6_definitions
from .pending10_ce10 import ce10_definitions
from .pending10_sufficiency import sufficiency_definitions

VERSION='CRISIS-PENDING10-FINAL-20261014-1'
CHANGED={'CR-RI3','CR-OP4','CR-NI6','CR-CE10','CR-CT10','CR-RE4','CR-GA1','CR-GA2'}

def final_definitions(definitions):
    return sufficiency_definitions(ce10_definitions(ni6_definitions(ri3_definitions(contextual_definitions(definitions)))))

class CrisisEvaluator(Protocol):
    def _pair(self,context,definitions,candidates=None,recovery=False):
        updated=final_definitions(definitions)
        original=self.provider
        seed=getattr(original,'seed',None)
        if isinstance(seed,dict) and any(k.split('.',1)[0] in CHANGED for k in seed):
            isolated=copy(original)
            isolated.seed={k:v for k,v in seed.items() if k.split('.',1)[0] not in CHANGED}
            self.provider=isolated
        try:return super()._pair(context,updated,candidates,recovery)
        finally:self.provider=original
