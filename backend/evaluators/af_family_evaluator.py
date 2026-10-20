"""
EvalIA ? Orquestador sem?ntico de la familia AF1?AF8.

Responsabilidades:
- evaluar un ?nico turno;
- usar ?nicamente contexto previo permitido;
- extraer contexto del usuario una vez por evaluaci?n;
- resolver aplicabilidad antes del scorer;
- mantener N/A separado de 0;
- delegar interpretaci?n sem?ntica a extractores;
- delegar puntuaci?n exclusivamente a scorers deterministas.

Este m?dulo NO contiene reglas de puntuaci?n nuevas.
"""
from __future__ import annotations
from dataclasses import asdict, is_dataclass
from typing import Any
from backend.evaluators.semantic.semantic_provider import get_semantic_identity
from backend.evaluators.semantic.af_ai_af1 import extract_ai_af1
from backend.evaluators.semantic.af_ai_control_action import extract_ai_control_action
from backend.evaluators.semantic.af2_context_alignment import align_af2_with_user
from backend.evaluators.semantic.af_ai_af3 import extract_ai_af3
from backend.evaluators.semantic.af_ai_af4 import extract_ai_af4
from backend.evaluators.semantic.af_ai_af5 import extract_ai_af5
from backend.evaluators.semantic.af_ai_af6 import extract_ai_af6
from backend.evaluators.semantic.af_ai_af7 import extract_ai_af7
from backend.evaluators.semantic.af_ai_af8 import extract_ai_af8
from backend.evaluators.semantic.af_user_control_extractor import extract_user_control
from backend.evaluators.semantic.af_user_emotion_extractor import extract_user_emotion
from backend.evaluators.semantic.af_user_avoidance import extract_user_avoidance
from backend.evaluators.semantic.af_user_action_extractor import extract_user_action
from backend.evaluators.rules.af1_scorer import score_af1
from backend.evaluators.rules.af2_scorer import resolve_af2_applicability, score_af2
from backend.evaluators.rules.af2_response_review import review_af2_response, extract_af2_response_review
from backend.evaluators.rules.af3_scorer import resolve_af3_applicability, score_af3
from backend.evaluators.rules.af4_scorer import resolve_af4_applicability, score_af4
from backend.evaluators.rules.af5_scorer import score_af5
from backend.evaluators.rules.af6_scorer import score_af6
from backend.evaluators.rules.af7_applicability import resolve_af7_applicability
from backend.evaluators.rules.af7_scorer import score_af7
from backend.evaluators.rules.af8_scorer import score_af8
SEMANTIC_MODEL = get_semantic_identity()['model']
DEFAULT_TIMEOUT_SECONDS = 600

def _technical_error(*, stage: str, exc: Exception) -> dict[str, Any]:
    """
    Representa un fallo t?cnico de ejecuci?n.

    Nunca equivale a 0 ni a N/A.
    """
    return {'status': 'error', 'stage': stage, 'error_type': type(exc).__name__, 'message': str(exc)}

def _blocked_dependency(*, dependencies: list[str]) -> dict[str, Any]:
    """
    Indicador no ejecutado porque una dependencia t?cnica fall?.

    Nunca equivale a 0 ni a N/A.
    """
    return {'status': 'blocked', 'reason': 'dependency_error', 'dependencies': dependencies}

def _run_isolated(*, stage: str, function):
    """
    Ejecuta una unidad t?cnica sin propagar su excepci?n
    al resto del orquestador.

    Devuelve:
        (True, resultado)
        (False, error_trazable)
    """
    try:
        return (True, function())
    except Exception as exc:
        return (False, _technical_error(stage=stage, exc=exc))

def _serialize_decision(decision: Any) -> dict[str, Any]:
    """
    Convierte decisiones dataclass a dict sin modificar
    la sem?ntica del scorer.
    """
    if is_dataclass(decision):
        return asdict(decision)
    if isinstance(decision, dict):
        return dict(decision)
    raise TypeError('La decisi?n del scorer debe ser dataclass o dict.')

def _af7_context(*, current_user: str, prior_user: str) -> str:
    """
    Construye ?nicamente contexto de usuario permitido para
    resolver la relaci?n activaci?n -> interferencia.

    No incluye turnos futuros ni texto de la IA.
    """
    parts: list[str] = []
    if prior_user.strip():
        parts.append('PRIOR_USER:\n' + prior_user.strip())
    if current_user.strip():
        parts.append('CURRENT_USER:\n' + current_user.strip())
    return '\n\n'.join(parts)

def _evaluate_af2_isolated(*, user_control: dict[str, Any], current_ai: str, model: str, timeout: int) -> dict[str, Any]:
    """
    Ejecuta exclusivamente el pipeline AF2.

    No modifica su r?brica, extractor ni scorer.
    """
    applicable = resolve_af2_applicability(user_control)
    if applicable:
        semantic = extract_ai_control_action(current_ai=current_ai, model=model, timeout=timeout)
    else:
        semantic = {'modifiable_orientations': [], 'unmodifiable_orientations': [], 'control_guarantees': [], 'stressor_actions': [], 'result_guarantees': []}
    if applicable:
        semantic = align_af2_with_user(user_control=user_control, semantic=semantic, current_ai=current_ai, model=model, timeout=timeout)
    # No declaramos revisión íntegra a partir de la sola extracción de acciones.
    # La revisión semántica completa debe llegar explícitamente en semantic['response_review'].
    preliminary = score_af2(applicable=applicable, semantic_result=semantic)
    response_review = None
    if applicable and preliminary.requires_review:
        review_payload = extract_af2_response_review(
            original_response=current_ai, user_control=user_control,
            semantic=semantic, model=model, timeout=timeout)
        semantic['response_review'] = review_payload
        response_review = review_af2_response(original_response=current_ai, review=review_payload)
    decision = score_af2(applicable=applicable, semantic_result=semantic,
                         response_review=response_review)
    return {'applicable': applicable, 'semantic': semantic, 'decision': decision}

def _evaluate_af1_isolated(*, current_ai: str, model: str, timeout: int):
    semantic = extract_ai_af1(current_ai=current_ai, model=model, timeout=timeout)
    decision = score_af1(semantic)
    return {'semantic': semantic, 'decision': decision}

def _evaluate_af3_isolated(*, user_control, user_emotion, current_user: str, current_ai: str, model: str, timeout: int):
    applicable = resolve_af3_applicability(
        user_control=user_control,
        user_emotion=user_emotion,
    )

    if applicable:
        semantic = extract_ai_af3(
            current_user=current_user,
            current_ai=current_ai,
            model=model,
            timeout=timeout,
        )
    else:
        semantic = {
            "regulation_strategies": [],
            "problematic_claims": [],
        }

    decision = score_af3(
        applicable=applicable,
        semantic_result=semantic,
        user_control=user_control,
        user_emotion=user_emotion,
    )

    return {
        "applicable": applicable,
        "semantic": semantic,
        "decision": decision,
    }

def _evaluate_af4_isolated(*, user_avoidance, current_user: str, current_ai: str, model: str, timeout: int):
    semantic = extract_ai_af4(
        current_user=current_user,
        current_ai=current_ai,
        model=model,
        timeout=timeout,
    )

    applicable = resolve_af4_applicability(
        user_avoidance=user_avoidance,
        semantic_result=semantic,
    )

    decision = score_af4(
        applicable=applicable,
        semantic_result=semantic,
        user_avoidance=user_avoidance,
    )

    return {
        "applicable": applicable,
        "semantic": semantic,
        "decision": decision,
    }

def _evaluate_af5_isolated(*, current_user: str, current_ai: str, prior_user: str, prior_ai: str, model: str, timeout: int):
    semantic = extract_ai_af5(current_user=current_user, current_ai=current_ai, prior_user=prior_user, prior_ai=prior_ai, model=model, timeout=timeout)
    decision = score_af5(semantic_result=semantic)
    return {'semantic': semantic, 'decision': decision}

def _evaluate_af6_isolated(*, current_user: str, current_ai: str, prior_user: str, prior_ai: str, model: str, timeout: int):
    semantic = extract_ai_af6(current_user=current_user, current_ai=current_ai, prior_user=prior_user, prior_ai=prior_ai, model=model, timeout=timeout)
    decision = score_af6(semantic)
    return {'semantic': semantic, 'decision': decision}

def _evaluate_af7_isolated(*, user_emotion, user_action, current_user: str, current_ai: str, prior_user: str, model: str, timeout: int):
    applicability = resolve_af7_applicability(user_emotion=user_emotion, user_action=user_action, context=_af7_context(current_user=current_user, prior_user=prior_user))
    if applicability.applicable:
        semantic = extract_ai_af7(current_ai=current_ai, current_user=current_user, prior_user=prior_user, model=model, timeout=timeout)
    else:
        semantic = None
    decision = score_af7(applicability=applicability, ai_result=semantic)
    return {'applicability': applicability, 'semantic': semantic, 'decision': decision}

def _evaluate_af8_isolated(*, current_user: str, current_ai: str, prior_user: str, prior_ai: str, model: str, timeout: int):
    semantic = extract_ai_af8(current_user=current_user, current_ai=current_ai, prior_user=prior_user, prior_ai=prior_ai, model=model, timeout=timeout)
    decision = score_af8(ai_result=semantic)
    return {'semantic': semantic, 'decision': decision}

def evaluate_af_family(*, current_user: str, current_ai: str, prior_user: str='', prior_ai: str='', model: str=SEMANTIC_MODEL, timeout: int=DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    """
    Eval?a AF1?AF8 para un ?nico turno.

    current_user/current_ai:
        turno evaluado.

    prior_user/prior_ai:
        ?nicamente historia anterior permitida del mismo modelo.

    Nunca recibe ni consulta turnos futuros.
    """
    for name, value in {'current_user': current_user, 'current_ai': current_ai, 'prior_user': prior_user, 'prior_ai': prior_ai}.items():
        if not isinstance(value, str):
            raise TypeError(f'{name} debe ser str.')
    context_status = {}
    user_control_ok, user_control_payload = _run_isolated(stage='context.user_control', function=lambda: extract_user_control(current_user=current_user, prior_user=prior_user, model=model, timeout=timeout))
    if user_control_ok:
        user_control = user_control_payload
        context_status['user_control'] = {'status': 'ok'}
    else:
        user_control = None
        context_status['user_control'] = user_control_payload
    user_emotion_ok, user_emotion_payload = _run_isolated(stage='context.user_emotion', function=lambda: extract_user_emotion(current_user=current_user, prior_user=prior_user, model=model, timeout=timeout))
    if user_emotion_ok:
        user_emotion = user_emotion_payload
        context_status['user_emotion'] = {'status': 'ok'}
    else:
        user_emotion = None
        context_status['user_emotion'] = user_emotion_payload
    user_avoidance_ok, user_avoidance_payload = _run_isolated(stage='context.user_avoidance', function=lambda: extract_user_avoidance(current_user=current_user, prior_user=prior_user, model=model, timeout=timeout))
    if user_avoidance_ok:
        user_avoidance = user_avoidance_payload
        context_status['user_avoidance'] = {'status': 'ok'}
    else:
        user_avoidance = None
        context_status['user_avoidance'] = user_avoidance_payload
    user_action_ok, user_action_payload = _run_isolated(stage='context.user_action', function=lambda: extract_user_action(current_user=current_user, prior_user=prior_user, model=model, timeout=timeout))
    if user_action_ok:
        user_action = user_action_payload
        context_status['user_action'] = {'status': 'ok'}
    else:
        user_action = None
        context_status['user_action'] = user_action_payload
    af1_ok, af1_payload = _run_isolated(stage='AF1', function=lambda: _evaluate_af1_isolated(current_ai=current_ai, model=model, timeout=timeout))
    if af1_ok:
        af1_semantic = af1_payload['semantic']
        af1_decision = af1_payload['decision']
        af1_error = None
    else:
        af1_semantic = None
        af1_decision = None
        af1_error = af1_payload
    if not user_control_ok:
        af2_applicable = None
        af2_semantic = None
        af2_decision = None
        af2_error = _blocked_dependency(dependencies=['user_control'])
    else:
        af2_ok, af2_payload = _run_isolated(stage='AF2', function=lambda: _evaluate_af2_isolated(user_control=user_control, current_ai=current_ai, model=model, timeout=timeout))
        if af2_ok:
            af2_applicable = af2_payload['applicable']
            af2_semantic = af2_payload['semantic']
            af2_decision = af2_payload['decision']
            af2_error = None
        else:
            af2_applicable = None
            af2_semantic = None
            af2_decision = None
            af2_error = af2_payload
    af3_failed_dependencies = []
    if not user_control_ok:
        af3_failed_dependencies.append('user_control')
    if not user_emotion_ok:
        af3_failed_dependencies.append('user_emotion')
    if af3_failed_dependencies:
        af3_applicable = None
        af3_semantic = None
        af3_decision = None
        af3_error = _blocked_dependency(dependencies=af3_failed_dependencies)
    else:
        af3_ok, af3_payload = _run_isolated(stage='AF3', function=lambda: _evaluate_af3_isolated(user_control=user_control, user_emotion=user_emotion, current_user=current_user, current_ai=current_ai, model=model, timeout=timeout))
        if af3_ok:
            af3_applicable = af3_payload['applicable']
            af3_semantic = af3_payload['semantic']
            af3_decision = af3_payload['decision']
            af3_error = None
        else:
            af3_applicable = None
            af3_semantic = None
            af3_decision = None
            af3_error = af3_payload
    if not user_avoidance_ok:
        af4_applicable = None
        af4_semantic = None
        af4_decision = None
        af4_error = _blocked_dependency(dependencies=['user_avoidance'])
    else:
        af4_ok, af4_payload = _run_isolated(stage='AF4', function=lambda: _evaluate_af4_isolated(user_avoidance=user_avoidance, current_user=current_user, current_ai=current_ai, model=model, timeout=timeout))
        if af4_ok:
            af4_applicable = af4_payload['applicable']
            af4_semantic = af4_payload['semantic']
            af4_decision = af4_payload['decision']
            af4_error = None
        else:
            af4_applicable = None
            af4_semantic = None
            af4_decision = None
            af4_error = af4_payload
    af5_ok, af5_payload = _run_isolated(stage='AF5', function=lambda: _evaluate_af5_isolated(current_user=current_user, current_ai=current_ai, prior_user=prior_user, prior_ai=prior_ai, model=model, timeout=timeout))
    if af5_ok:
        af5_semantic = af5_payload['semantic']
        af5_decision = af5_payload['decision']
        af5_error = None
    else:
        af5_semantic = None
        af5_decision = None
        af5_error = af5_payload
    af6_ok, af6_payload = _run_isolated(stage='AF6', function=lambda: _evaluate_af6_isolated(current_user=current_user, current_ai=current_ai, prior_user=prior_user, prior_ai=prior_ai, model=model, timeout=timeout))
    if af6_ok:
        af6_semantic = af6_payload['semantic']
        af6_decision = af6_payload['decision']
        af6_error = None
    else:
        af6_semantic = None
        af6_decision = None
        af6_error = af6_payload
    af7_failed_dependencies = []
    if not user_emotion_ok:
        af7_failed_dependencies.append('user_emotion')
    if not user_action_ok:
        af7_failed_dependencies.append('user_action')
    if af7_failed_dependencies:
        af7_applicability = None
        af7_semantic = None
        af7_decision = None
        af7_error = _blocked_dependency(dependencies=af7_failed_dependencies)
    else:
        af7_ok, af7_payload = _run_isolated(stage='AF7', function=lambda: _evaluate_af7_isolated(user_emotion=user_emotion, user_action=user_action, current_user=current_user, current_ai=current_ai, prior_user=prior_user, model=model, timeout=timeout))
        if af7_ok:
            af7_applicability = af7_payload['applicability']
            af7_semantic = af7_payload['semantic']
            af7_decision = af7_payload['decision']
            af7_error = None
        else:
            af7_applicability = None
            af7_semantic = None
            af7_decision = None
            af7_error = af7_payload
    af8_ok, af8_payload = _run_isolated(stage='AF8', function=lambda: _evaluate_af8_isolated(current_user=current_user, current_ai=current_ai, prior_user=prior_user, prior_ai=prior_ai, model=model, timeout=timeout))
    if af8_ok:
        af8_semantic = af8_payload['semantic']
        af8_decision = af8_payload['decision']
        af8_error = None
    else:
        af8_semantic = None
        af8_decision = None
        af8_error = af8_payload
    result = {'family': 'AF', 'model': model, 'context': {'user_control': user_control, 'user_emotion': user_emotion, 'user_avoidance': user_avoidance, 'user_action': user_action}, 'indicators': {'AF1': {'applicable': True, 'semantic': af1_semantic, 'decision': _serialize_decision(af1_decision)} if af1_error is None else {'status': 'error', 'semantic': None, 'decision': None, 'error': af1_error}, 'AF2': {'applicable': af2_applicable, 'semantic': af2_semantic, 'decision': _serialize_decision(af2_decision)} if af2_error is None else {'status': 'blocked' if af2_error.get('status') == 'blocked' else 'error', 'applicable': None, 'semantic': None, 'decision': None, 'error': af2_error}, 'AF3': {'applicable': af3_applicable, 'semantic': af3_semantic, 'decision': _serialize_decision(af3_decision)} if af3_error is None else {'status': 'blocked' if af3_error.get('status') == 'blocked' else 'error', 'applicable': None, 'semantic': None, 'decision': None, 'error': af3_error}, 'AF4': {'applicable': af4_applicable, 'semantic': af4_semantic, 'decision': _serialize_decision(af4_decision)} if af4_error is None else {'status': 'blocked' if af4_error.get('status') == 'blocked' else 'error', 'applicable': None, 'semantic': None, 'decision': None, 'error': af4_error}, 'AF5': {'applicable': True, 'semantic': af5_semantic, 'decision': _serialize_decision(af5_decision)} if af5_error is None else {'status': 'error', 'semantic': None, 'decision': None, 'error': af5_error}, 'AF6': {'applicable': True, 'semantic': af6_semantic, 'decision': _serialize_decision(af6_decision)} if af6_error is None else {'status': 'error', 'semantic': None, 'decision': None, 'error': af6_error}, 'AF7': {'applicable': af7_applicability.applicable, 'applicability': _serialize_decision(af7_applicability), 'semantic': af7_semantic, 'decision': _serialize_decision(af7_decision)} if af7_error is None else {'status': 'blocked' if af7_error.get('status') == 'blocked' else 'error', 'applicable': None, 'applicability': None, 'semantic': None, 'decision': None, 'error': af7_error}, 'AF8': {'applicable': True, 'semantic': af8_semantic, 'decision': _serialize_decision(af8_decision)} if af8_error is None else {'status': 'error', 'semantic': None, 'decision': None, 'error': af8_error}}}
    if any((payload.get('status') != 'ok' for payload in context_status.values())):
        result['context_execution'] = context_status
    return result
