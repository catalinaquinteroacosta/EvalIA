"""Independent CRISIS protocol candidate. Existing scorer/gates unchanged.

Uses the same crisis_semantic package path as the frozen execution environment.
No provider creation, recovery retry or paid capability is implicit.
"""
from crisis_semantic.pipeline import CrisisEvaluator as FrozenEvaluator,EXTRACT,VERIFY,PROMPT_VERSION
from crisis_semantic.domain import digest
from crisis_semantic.evidence import output_schema,reconcile as frozen_reconcile,EvidenceError,validate_payload
from copy import deepcopy

VERSION='CRISIS-COMPLETE-REVIEW-CANDIDATE-20261014-1'
def reconcile_complete(a,b,definitions,context,external_attestations=()):
    if any(not isinstance(r,dict) or r.get('reviewed_entire_context') is not True for r in (a,b)):
        raise EvidenceError('incomplete_context_review')
    return frozen_reconcile(a,b,definitions,context,external_attestations)

class CrisisEvaluator(FrozenEvaluator):
    def __init__(self,provider,*,external_attestations=()):
        super().__init__(provider,recovery=False,external_attestations=external_attestations)

    def evaluate(self,context,codes):
        result=super().evaluate(context,codes)
        for row in result['results']:
            if row['status']=='BLOCKED' and any('incomplete_context_review' in d.get('issues',[]) for d in row.get('verified_decisions',{}).values()):
                row['technical_cause']='incomplete_context_review'
        return result

    def _pair(self,context,defs,candidates=None,recovery=False):
        codes=list(dict.fromkeys(d['code'] for d in defs.values()))
        content={'conversation':context.payload(),'predicates':defs,
          'official_questions':{c:self.contracts[c]['official_question']['text'] for c in codes},
          'official_gates':{c:self.contracts[c]['applicability']['text'] for c in codes},
          'external_attestations':list(self.external_attestations)}
        identity={'rubric_sha256':self.manifest['source_sha256'],'prompt_version':PROMPT_VERSION,
          'catalog_sha256':digest(defs),'recovery':False}
        schema=output_schema(defs,context)
        a=self.provider.run('extract',EXTRACT,deepcopy(content),deepcopy(schema),list(defs),deepcopy(identity))
        b=self.provider.run('verify',VERIFY,deepcopy(content),deepcopy(schema),list(defs),deepcopy(identity))
        # An independent temporal gate (CE10 without two prior turns) does
        # not need semantic review. Preserve it while rejecting ALL semantic
        # assertions from an incomplete pair, rather than raising batch-wide.
        validate_payload(a,defs);validate_payload(b,defs)
        if a['reviewed_entire_context'] is not True or b['reviewed_entire_context'] is not True:
            left={r['id']:r for r in a['claims']};right={r['id']:r for r in b['claims']}
            decisions={k:{'value':None,'extraction':left[k],'verification':right[k],
                'issues':['incomplete_context_review']} for k in defs}
            return ({k:None for k in defs},decisions,[{'id':k,'cause':'incomplete_context_review'} for k in defs])
        return reconcile_complete(a,b,defs,context,self.external_attestations)
