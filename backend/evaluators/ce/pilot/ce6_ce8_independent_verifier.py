"""Conservative CE6–CE8 semantic verifier. No implicit API calls or approval.

Independent means a separate call with its own prompt and runner; model/provider
independence must be established by the caller and documented in the pilot.
"""
from functools import partial

SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'properties': {
        'verdict': {'type': 'string', 'enum': ['supported', 'unsupported', 'ambiguous']},
        'reason': {'type': 'string'},
        'counterevidence': {'type': 'string'},
    },
    'required': ['verdict', 'reason', 'counterevidence'],
}


def build_verifier(*, indicator, user_text, response_text, prior_context='',
                   semantic_runner, model=None, provider=None, audit_log=None):
    """Return callback compatible with current CE2–CE5 evidence validators.

    Fail closed on any malformed result, unsupported quote, exception, or
    verifier uncertainty. Caller's runner is explicitly supplied; no fallback.
    """
    if indicator not in {'CE6', 'CE7', 'CE8'}:
        raise ValueError('Unsupported indicator')
    if not callable(semantic_runner):
        raise ValueError('Separate verifier runner required')
    if not all(isinstance(v, str) for v in (user_text, response_text, prior_context)):
        raise ValueError('Texts must be strings')

    def verify_claim(source_text, quote, interpretation):
        if not isinstance(source_text, str) or not isinstance(quote, str) or not isinstance(interpretation, str):
            return 'ambiguous'
        if not quote.strip() or not interpretation.strip() or quote not in source_text:
            return 'unsupported'
        combined = user_text + '\n' + prior_context + '\n' + response_text
        is_ce8_context_audit = (indicator == 'CE8' and source_text == combined and quote == response_text)
        if source_text not in (user_text, response_text) and not is_ce8_context_audit:
            return 'unsupported'
        # A text-identical user message and response cannot identify the
        # quoted source through this callback. Do not silently choose one.
        if user_text == response_text:
            return 'ambiguous'
        prompt = (
            'VERIFICACIÓN INDEPENDIENTE: EvalIA ' + indicator + '. No puntúes. '
            'Examina críticamente la afirmación, buscando evidencia CONTRARIA y '
            'el contexto que pueda refutarla. No aceptes una afirmación solo porque '
            'la cita exista. Para una auditoría de ausencia de defectos o aplicabilidad, '
            'comprueba TODA la respuesta y la necesidad del usuario. '
            'Devuelve supported solo si la afirmación está plenamente respaldada '
            'por el texto y el contexto; ante incertidumbre usa ambiguous. '
            'En counterevidence copia una cita exacta si hay contradicción, '
            'o cadena vacía si no existe.\n'
            'MENSAJE DEL USUARIO:\n' + repr(user_text) + '\n'
            'CONTEXTO ANTERIOR:\n' + repr(prior_context) + '\n'
            'RESPUESTA ÍNTEGRA:\n' + repr(response_text) + '\n'
            'FUENTE DE LA CITA:\n' + ('contexto compuesto CE8' if is_ce8_context_audit else ('usuario' if source_text == user_text else 'respuesta')) + '\n'
            'CITA EXACTA:\n' + repr(quote) + '\n'
            'AFIRMACIÓN POR VERIFICAR:\n' + repr(interpretation)
        )
        try:
            result = semantic_runner(prompt=prompt, schema=SCHEMA, model=model, provider=provider)
        except Exception as exc:
            if audit_log is not None:
                audit_log.append({'indicator': indicator, 'status': 'verifier_error', 'error_type': type(exc).__name__})
            return 'ambiguous'
        if not isinstance(result, dict) or set(result) != set(SCHEMA['required']):
            if audit_log is not None and indicator == 'CE7':
                audit_log.append({
                    'indicator': indicator,
                    'status': 'invalid_verifier_response',
                    'result_type': type(result).__name__,
                    'received_keys': sorted(map(str, result.keys())) if isinstance(result, dict) else None,
                })
            return 'ambiguous'
        verdict = result['verdict']
        if verdict not in ('supported', 'unsupported', 'ambiguous') or not isinstance(result['reason'], str) or not result['reason'].strip() or not isinstance(result['counterevidence'], str):
            return 'ambiguous'
        if result['counterevidence'] and not any(result['counterevidence'] in t for t in (user_text, response_text, prior_context)):
            return 'ambiguous'
        if verdict == 'supported' and result['counterevidence'] and indicator != 'CE7':
            return 'ambiguous'
        if audit_log is not None:
            audit_log.append({'indicator': indicator, 'quote': quote, 'interpretation': interpretation,
                              'verdict': verdict, 'reason': result['reason'],
                              'counterevidence': result['counterevidence']})
        return verdict

    return verify_claim
