"""CE6-CE8 separate integration; live API opt-in only."""
from importlib import import_module
BRIDGES={f'CE{i}':(f'ce_{chr(96+i)}.ce{i}_provider_bridge',f'extract_ce{i}_draft',f'evaluate_ce{i}_with_verifier') for i in (6,7,8)}
def evaluate(*,indicator,user_text,response_text,prior_context='',verify_claim=None,semantic_runner=None,allow_live=False,model=None,provider=None):
    if indicator not in BRIDGES: raise ValueError('Only CE6-CE8')
    if not callable(verify_claim): raise ValueError('Independent verifier mandatory')
    if semantic_runner is None and not allow_live: raise ValueError('Live API disabled')
    module,extract_name,evaluate_name=BRIDGES[indicator]
    bridge=import_module('backend.evaluators.ce.'+module)
    draft=getattr(bridge,extract_name)(user_text=user_text,response_text=response_text,prior_context=prior_context,model=model,provider=provider,semantic_runner=semantic_runner)
    if draft.get('status')!='unverified_draft': raise ValueError('Invalid draft')
    extraction = draft['extraction']
    if indicator in ('CE7', 'CE8'):
        from .ce78_reconciliation import reconcile_literal_claims
        recovery = reconcile_literal_claims(
            indicator=indicator,
            user_text=user_text,
            response_text=response_text,
            extraction=extraction,
            semantic_runner=semantic_runner,
            model=model,
            provider=provider,
        )
        if recovery['status'] == 'BLOCKED':
            return {
                'indicator': indicator,
                'draft_identity': draft.get('identity'),
                'status': 'BLOCKED',
                'score': None,
                'reason': recovery['reason'],
                'evidence_verification_required': True,
            }
        extraction = recovery['extraction']
    result=getattr(bridge,evaluate_name)(user_text=user_text,response_text=response_text,prior_context=prior_context,extraction=extraction,verify_claim=verify_claim)
    if result['status']!='scored' and result.get('score') is not None: raise ValueError('Invalid pending score')
    return {'indicator':indicator,'draft_identity':draft.get('identity'),'status':result['status'],'score':result.get('score'),'evidence_verification_required':True}
