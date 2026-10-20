"""CE6-CE8 orchestration: requires explicit separate verifier runner."""
from backend.evaluators.ce.pilot.ce6_ce8_independent_verifier import build_verifier
from backend.evaluators.ce.pilot.integrate_ce6_ce8 import evaluate

def evaluate_verified(*, indicator, user_text, response_text, extraction_runner, verifier_runner, prior_context='', model=None, provider=None, verifier_model=None, verifier_provider=None, audit_log=None):
    if extraction_runner is verifier_runner:
        raise ValueError('Extraction and verifier runners must be separate')
    verify_claim = build_verifier(indicator=indicator, user_text=user_text, response_text=response_text, prior_context=prior_context, semantic_runner=verifier_runner, model=verifier_model, provider=verifier_provider, audit_log=audit_log)
    return evaluate(indicator=indicator, user_text=user_text, response_text=response_text, prior_context=prior_context, verify_claim=verify_claim, semantic_runner=extraction_runner, model=model, provider=provider)
