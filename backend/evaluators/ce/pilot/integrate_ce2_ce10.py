"""Unified opt-in dispatcher for CE2–CE10. CE1 is intentionally excluded.

CE2–CE8 use the existing independent verify_claim callback. CE9–CE10
require distinct extraction and verification runners. Never silently use
one runner for both stages, or call live APIs without explicit opt-in.
"""
from . import integrate_ce2_ce5, integrate_ce6_ce8
from .ce9_ce10_runner import evaluate_verified


def evaluate(*, indicator, user_text, response_text, prior_context='',
             verify_claim=None, semantic_runner=None, allow_live=False,
             model=None, provider=None, history=None, verifier_runner=None,
             verifier_model=None, verifier_provider=None, audit_log=None):
    if indicator not in {f'CE{i}' for i in range(2, 11)}:
        raise ValueError('Only CE2–CE10; CE1 is pending separately')
    if not isinstance(user_text, str) or not user_text.strip():
        raise ValueError('Missing user text')
    if not isinstance(response_text, str) or not response_text.strip():
        raise ValueError('Missing response text')
    if not isinstance(prior_context, str):
        raise ValueError('Invalid prior context')
    if indicator in ('CE9', 'CE10'):
        if indicator == 'CE10':
            if history is None:
                raise ValueError('Explicit same-model history required; [] means first turn')
            if not isinstance(history, list) or any(
                not isinstance(turn, dict) or set(turn) != {'role', 'text'}
                or turn['role'] not in ('user', 'assistant')
                or not isinstance(turn['text'], str) or not turn['text'].strip()
                for turn in history
            ):
                raise ValueError('Invalid same-model history')
            if not history:
                return {'indicator': 'CE10', 'status': 'not_applicable',
                        'score': None, 'reason': 'first_turn'}
        if not callable(semantic_runner) or not callable(verifier_runner):
            raise ValueError('Separate extraction and verification runners mandatory')
        if semantic_runner is verifier_runner:
            raise ValueError('Extraction and verification runners must be distinct')
        return evaluate_verified(
            indicator=indicator, user_text=user_text, response_text=response_text,
            extraction_runner=semantic_runner, verifier_runner=verifier_runner,
            prior_context=prior_context, history=history, model=model,
            provider=provider, verifier_model=verifier_model,
            verifier_provider=verifier_provider, audit_log=audit_log)
    if not callable(verify_claim):
        raise ValueError('Independent verify_claim mandatory for CE2–CE8')
    if semantic_runner is None and not allow_live:
        raise ValueError('Live API disabled; provide semantic_runner or allow_live=True')
    integration = integrate_ce2_ce5 if int(indicator[2:]) <= 5 else integrate_ce6_ce8
    return integration.evaluate(
        indicator=indicator, user_text=user_text, response_text=response_text,
        prior_context=prior_context, verify_claim=verify_claim,
        semantic_runner=semantic_runner, allow_live=allow_live,
        model=model, provider=provider)
