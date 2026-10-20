"""EvalIA: explicit fail-closed CE2–CE5 pipeline. CE1 remains pending.

No real API calls unless caller supplies a semantic runner or explicitly calls live.
A verifier must be supplied independently; no auto-approval is provided.
"""
from importlib import import_module

BRIDGES = {
    'CE2': ('ce_b.ce2_provider_bridge', 'extract_ce2_draft', 'evaluate_ce2_with_verifier'),
    'CE3': ('ce_c.ce3_provider_bridge', 'extract_ce3_draft', 'evaluate_ce3_with_verifier'),
    'CE4': ('ce_d.ce4_provider_bridge', 'extract_ce4_draft', 'evaluate_ce4_with_verifier'),
    'CE5': ('ce_e.ce5_provider_bridge', 'extract_ce5_draft', 'evaluate_ce5_with_verifier'),
}


def evaluate(*, indicator, user_text, response_text, prior_context='', verify_claim=None,
             semantic_runner=None, allow_live=False, model=None, provider=None):
    """Extract -> validate evidence -> deterministic scoring, preserving pending statuses.

    The verifier must independently validate semantics and context. This orchestration
    does not establish verifier independence, which requires separate validation.
    """
    if indicator not in BRIDGES:
        raise ValueError('Only CE2–CE5 are wired; CE1 needs its own integration')
    if not callable(verify_claim):
        raise ValueError('An independent verify_claim callback is mandatory')
    if semantic_runner is None and not allow_live:
        raise ValueError('Live API disabled: supply semantic_runner or allow_live=True')
    module_name, extract_name, evaluate_name = BRIDGES[indicator]
    mod = import_module('backend.evaluators.ce.' + module_name)
    draft = getattr(mod, extract_name)(
        user_text=user_text, response_text=response_text, prior_context=prior_context,
        model=model, provider=provider, semantic_runner=semantic_runner)
    if draft.get('status') != 'unverified_draft' or not isinstance(draft.get('extraction'), dict):
        raise ValueError('Invalid draft envelope')
    result = getattr(mod, evaluate_name)(
        user_text=user_text, response_text=response_text,
        extraction=draft['extraction'], verify_claim=verify_claim)
    if not isinstance(result, dict) or 'status' not in result:
        raise ValueError('Invalid scorer result')
    if result['status'] != 'scored' and result.get('score') is not None:
        raise ValueError('Non-scored result must not contain numeric score')
    return {'indicator': indicator, 'draft_identity': draft.get('identity'),
            'status': result['status'], 'score': result.get('score'),
            'evidence_verification_required': True,
            **({'missing_fields': result['missing_fields']} if 'missing_fields' in result else {})}
