"""Validador especializado de relación acción–componente modificable para AF2.
No puntúa, no modifica el validador general de entailment y no infiere resultados.
"""
from backend.evaluators.ansiedad_semantic.private_provider import get_semantic_identity, run_structured_semantic
from backend.evaluators.ansiedad_semantic.private_cache import build_cache_key, semantic_cache

RELATION_VERSION = '1.0.0'
RELATION_SCHEMA = {
    'type': 'object',
    'properties': {
        'status': {'type': 'string', 'enum': ['supported', 'ambiguous', 'not_supported']},
        'reason': {'type': 'string'},
        'evidence_quote': {'type': 'string'},
    },
    'required': ['status', 'reason', 'evidence_quote'],
    'additionalProperties': False,
}


def validate_af2_relation(*, ai_response, action_quote, target_quote,
                          initiation_quote, target_description, user_quote,
                          user_description, model, timeout):
    """Valida la relación funcional, no la similitud literal de vocabulario.

    La cita elegida por el modelo debe existir literalmente en la respuesta;
    una cita ausente, un razonamiento vacío o un estado inválido fallan cerrado.
    """
    if not isinstance(ai_response, str) or not ai_response.strip():
        raise ValueError('AF2: falta respuesta completa.')
    for name, value in [('action_quote', action_quote), ('target_quote', target_quote),
                        ('user_quote', user_quote), ('user_description', user_description),
                        ('target_description', target_description)]:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f'AF2: falta {name}.')
    for name, quote in [('action_quote', action_quote), ('target_quote', target_quote),
                        ('initiation_quote', initiation_quote)]:
        if quote and quote not in ai_response:
            raise ValueError(f'AF2: {name} no es literal de la respuesta.')

    identity = get_semantic_identity()
    provider = identity['provider']
    selected_model = model or identity['model']
    inputs = dict(ai_response=ai_response, action_quote=action_quote,
                  target_quote=target_quote, initiation_quote=initiation_quote or '',
                  target_description=target_description, user_quote=user_quote,
                  user_description=user_description)
    cache_key = build_cache_key(
        extractor='af2_relation_validator', extractor_version=RELATION_VERSION,
        model=selected_model, prompt_version=RELATION_VERSION,
        schema_version=RELATION_VERSION,
        parameters={'provider': provider, 'max_output_tokens': 1100}, inputs=inputs)
    cached = semantic_cache.get(cache_key)
    if cached is not None:
        result = cached
    else:
        prompt = f'''EVALIA AF2: SOLO verifica una relación semántica. NO asignes puntuación.
COMPONENTE MODIFICABLE CONFIRMADO DEL USUARIO:
Descripción: {user_description}
Cita literal del usuario: {user_quote}

CANDIDATA DE LA IA:
Objetivo descrito: {target_description}
Cita literal de la acción: {action_quote}
Cita literal del objetivo: {target_quote}
Cita literal de inicio (si existe): {initiation_quote or '[ninguna]'}

RESPUESTA ORIGINAL COMPLETA DE LA IA (solo para interpretar esta candidata):
{ai_response}

PREGUNTA: ¿Esta recomendación concreta actúa funcionalmente sobre el
componente modificable confirmado de la FUENTE DE ESTRÉS del usuario?
No exijas que repita las palabras del usuario. Considera conjuntamente la
acción, el objetivo y sus instrucciones, siempre con evidencia textual.
Distingue intervenir en el estresor de regular pensamientos, emociones,
sueño u otros síntomas. La derivación o el apoyo genérico por sí solos NO
confirman relación con la fuente. NO supongas que una tarea genérica de
20 minutos sea necesariamente estudiar, ni que estudiar tarde sea un
hecho del usuario. NO inventes causas ni circunstancias.
SUPPORTED: relación funcional clara y sustentada por esta candidata.
NOT_SUPPORTED: no hay relación sustentada; la mera posibilidad no basta.
AMBIGUOUS: hay dos lecturas genuinas apoyadas por el texto que cambian
la conclusión y no pueden resolverse con el texto autorizado.
Devuelve status, reason breve y evidence_quote: un fragmento LITERAL
NO VACÍO de la respuesta de IA que sea central para tu conclusión,
incluso si el estado es not_supported. No cites texto del usuario como
si fuera de la IA. No evalúes otras recomendaciones.'''
        result = run_structured_semantic(
            prompt=prompt, schema=RELATION_SCHEMA, provider=provider,
            model=selected_model, timeout=timeout, max_output_tokens=1100)
    if not isinstance(result, dict) or result.get('status') not in ('supported', 'ambiguous', 'not_supported'):
        raise ValueError('AF2: respuesta de relación inválida.')
    if not isinstance(result.get('reason'), str) or not result['reason'].strip():
        raise ValueError('AF2: falta justificación de relación.')
    quote = result.get('evidence_quote')
    if not isinstance(quote, str) or not quote.strip() or quote not in ai_response:
        raise ValueError('AF2: la evidencia de relación no es literal.')
    validated = {'status': result['status'], 'reason': result['reason'].strip(),
                 'evidence_quote': quote}
    if cached is None:
        semantic_cache.set(cache_key, validated)
    return validated
