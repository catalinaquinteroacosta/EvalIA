"""Final isolated composition: CE10 doubt is not an asserted contradiction."""
from copy import copy
from .pending10_release import final_definitions as previous_definitions,CHANGED
from .pending10_ce10_opposite import ce10_opposite_definitions
from .crisis import CrisisEvaluator as Protocol

VERSION='CRISIS-PENDING10-RELEASE-20261014-3'
def final_definitions(definitions):
    return ce10_opposite_definitions(previous_definitions(definitions))
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
