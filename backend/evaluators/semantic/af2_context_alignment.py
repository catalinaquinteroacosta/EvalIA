"""AF2: alinea cada candidata con el componente modificable, sin exigir coincidencia léxica."""
from copy import deepcopy
from backend.evaluators.semantic.af2_relation_validator import validate_af2_relation
from backend.evaluators.semantic.af_user_control_extractor import control_item_is_confirmed

ALIGNMENT_VERSION = '3.6.0'


def align_af2_with_user(*, user_control, semantic, current_ai, model, timeout):
    components = [c for c in user_control.get('modifiable_components', [])
                  if isinstance(c, dict) and control_item_is_confirmed(c)]
    if not components:
        raise ValueError('AF2 requiere componente modificable confirmado.')
    if not isinstance(current_ai, str) or not current_ai.strip():
        raise ValueError('AF2 requiere respuesta original completa.')

    def verify(*, target, action_quote, target_quote, initiation_quote=''):
        if not isinstance(target, str) or not target.strip():
            raise ValueError('AF2: falta descripción del objetivo de la IA.')
        if not isinstance(action_quote, str) or not action_quote.strip():
            raise ValueError('AF2: falta evidencia literal de candidata.')
        checks = []
        for component in components:
            desc = component.get('description')
            quote = component.get('evidence', {}).get('quote')
            if not isinstance(desc, str) or not desc.strip() or not isinstance(quote, str) or not quote.strip():
                raise ValueError('AF2: componente sin descripción o cita del usuario.')
            result = validate_af2_relation(
                ai_response=current_ai, action_quote=action_quote,
                target_quote=target_quote or action_quote,
                initiation_quote=initiation_quote or '',
                target_description=target, user_quote=quote,
                user_description=desc, model=model, timeout=timeout)
            checks.append({'user_description': desc, 'user_quote': quote, 'result': result})
        status = ('supported' if any(c['result']['status'] == 'supported' for c in checks)
                  else 'ambiguous' if any(c['result']['status'] == 'ambiguous' for c in checks)
                  else 'not_supported')
        return {'status': status, 'checks': checks}

    result = deepcopy(semantic)
    for action in result.get('stressor_actions', []):
        validation = action.get('semantic_validation', {})
        if validation.get('action_target', {}).get('status') == 'supported':
            evidence = action.get('evidence', {})
            relation = verify(target=action.get('target_description'),
                              action_quote=evidence.get('action_quote'),
                              target_quote=evidence.get('target_quote'),
                              initiation_quote=evidence.get('initiation_quote'))
            validation['user_alignment'] = relation
            if relation['status'] != 'supported':
                validation['action_target'] = {
                    'status': relation['status'],
                    'reason': 'Relación con el estresor no confirmada; revisar user_alignment.'}
    for target in result.get('stressor_targets', []):
        if target.get('semantic_validation', {}).get('status') == 'supported':
            evidence = target.get('evidence', {})
            relation = verify(target=target.get('target_description'),
                              action_quote=evidence.get('quote'),
                              target_quote=evidence.get('quote'))
            target['user_alignment'] = relation
            if relation['status'] != 'supported':
                target['semantic_validation'] = {
                    'status': relation['status'],
                    'reason': 'Objetivo no confirmado frente al estresor; revisar user_alignment.'}
    return result
