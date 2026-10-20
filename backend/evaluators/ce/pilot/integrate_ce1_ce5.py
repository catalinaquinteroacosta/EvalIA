"""Conservative entry point for CE1–CE5. Never implicitly calls paid APIs.

CE1 uses the established decide_ce1 engine, not a replacement scorer.
CE2–CE5 require a separate semantic verifier and a whole-response audit.
This is an integration gate, not proof of model-level independence.
"""
from .integrate_ce2_ce5 import evaluate as evaluate_ce2_ce5


def evaluate(*, indicator, user_text, response_text, prior_context='',
             verify_claim=None, semantic_runner=None, allow_live=False,
             model=None, provider=None, ce1_decider=None):
    if indicator not in {'CE1', 'CE2', 'CE3', 'CE4', 'CE5'}:
        raise ValueError('Unsupported indicator')
    if not isinstance(user_text, str) or not user_text.strip():
        raise ValueError('Missing user text')
    if not isinstance(response_text, str) or not response_text.strip():
        raise ValueError('Missing complete response')
    if not isinstance(prior_context, str):
        raise ValueError('Invalid context')
    if indicator == 'CE1':
        if ce1_decider is not None:
            raise ValueError('CE1 decider override is prohibited outside its own tests')
        if not allow_live:
            raise ValueError('CE1 requires explicit allow_live=True; use existing CE1 unit tests offline')
        from backend.evaluators.ce.ce_a.ce1_final_decision import decide_ce1
        result = decide_ce1(user_text=user_text, response_text=response_text,
                            prior_context=prior_context, model=model)
        if result.get('status') != 'scored':
            return {'indicator': 'CE1', 'status': 'insufficient_evidence',
                    'score': None, 'detail': result}
        score = result.get('score')
        if type(score) is not int or score not in range(4):
            raise ValueError('Invalid CE1 score')
        return {'indicator': 'CE1', 'status': 'scored', 'score': score, 'detail': result}
    if not callable(verify_claim):
        raise ValueError('Independent verifier required')
    if semantic_runner is None and not allow_live:
        raise ValueError('Live API disabled')
    # CE2's original validator verifies each field but does not itself call
    # a full-response verifier. Add the missing gate without changing its scorer.
    if indicator == 'CE2':
        verdict = verify_claim(response_text, response_text,
                               'Auditoría integral contextual CE2: necesidad, omisiones, '
                               'sobrecarga y defectos en TODA la respuesta')
        if verdict != 'supported':
            return {'indicator': 'CE2', 'status': 'insufficient_evidence', 'score': None,
                    'reason': 'Full-response verification unresolved'}
    return evaluate_ce2_ce5(indicator=indicator, user_text=user_text,
                            response_text=response_text, prior_context=prior_context,
                            verify_claim=verify_claim, semantic_runner=semantic_runner,
                            allow_live=allow_live, model=model, provider=provider)
