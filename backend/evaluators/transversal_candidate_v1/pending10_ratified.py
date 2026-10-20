"""Require the current qualification record, not a legacy qualified-code flag."""
from copy import copy,deepcopy
from crisis_semantic.predicate_catalog import definitions
from .pending10_release_final import CrisisEvaluator as Selected,final_definitions
from .pending10_qualification import bind_qualification

VERSION='CRISIS-PENDING10-RATIFIED-20261014-1'

class CrisisEvaluator(Selected):
    def evaluate(self,context,codes):
        original=self.provider
        if any(code in ('CR-RI2','CR-CE10') for code in codes):
            isolated=copy(original)
            isolated.qualified_components=set(getattr(original,'qualified_components',set()))
            records=getattr(original,'qualification_records',{})
            isolated.qualification_records=deepcopy(records) if isinstance(records,dict) else {}
            for code in ('CR-RI2','CR-CE10'):
                if code not in codes:continue
                proof=isolated.qualification_records.get(code)
                isolated.qualified_components.discard(code)
                if proof:
                    try:bind_qualification(isolated,code,proof,final_definitions(definitions(self.contracts,[code])))
                    except (ValueError,TypeError,KeyError,AttributeError):pass
            self.provider=isolated
        try:return super().evaluate(context,codes)
        finally:self.provider=original
