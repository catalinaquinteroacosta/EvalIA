"""Conservative CE2–CE5 semantic verifier. No implicit API calls or approval.

Independent means a separate call with its own prompt and runner; model/provider
independence must be established by the caller and documented in the pilot.
"""
from functools import partial
import re

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
    if indicator not in {'CE2', 'CE3', 'CE4', 'CE5'}:
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
        if source_text not in (user_text, response_text):
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
            'COUNTEREVIDENCE tiene una semantica estricta: contiene SOLO una cita exacta '
            'que CONTRADIGA la AFIRMACION POR VERIFICAR. No coloques en counterevidence '
            'evidencia que APOYA la afirmacion, ejemplos del defecto que la afirmacion '
            'describe, ni fragmentos que simplemente justifican el verdict. '
            'Si la afirmacion sostiene que existe un defecto (por ejemplo desorden, '
            'ambiguedad o tecnicismo), una cita que MUESTRA ese defecto es evidencia '
            'a favor y NO counterevidence. '
            'Si verdict=supported, counterevidence debe ser cadena vacia; si encuentras '
            'una contradiccion real que impide respaldo pleno, usa unsupported o ambiguous '
            'segun corresponda y copia alli la cita contradictoria.\n'
            + ('ALCANCE ESTRICTO CE2: Verifica cada campo por separado, sin usar defectos\n'
             'de otros campos para declararlo ambiguo. need_coverage mide cobertura\n'
             'de la necesidad; overload mide EXCLUSIVAMENTE exceso, redundancia o\n'
             'irrelevancia de contenido que sobrecarga. Una respuesta vacía o\n'
             'breve que omite la necesidad puede tener need_coverage=absent y\n'
             'overload=none simultáneamente. Para overload=none, si toda la\n'
             'respuesta es breve y no presenta contenido excesivo, redundante\n'
             'o irrelevante, no declares ambiguous SOLO por falta de cobertura.\n'
             'No apruebes overload=none cuando existan contenidos innecesarios\n'
             'o indicios reales de sobrecarga; ante duda genuina conserva\n'
             'ambiguous. secondary_defect debe ser independiente de cobertura\n'
             'y sobrecarga.\n' if indicator == 'CE2' else '') +
            ('CONTROL DE COHERENCIA CE4: El veredicto debe coincidir con la\n'
               'JUSTIFICACIÓN. Si declaras substantial pero la explicación\n'
               'afirma que la estructura es adecuada o niega una dificultad\n'
               'sustancial, devuelve unsupported, NO supported. Distingue\n'
               'limitación visual secundaria de dificultad sustancial real.\n'
               'Si la evidencia admite dos niveles incompatibles, usa ambiguous.\n'
               if indicator == 'CE4' else '') +
            'MENSAJE DEL USUARIO:\n' + repr(user_text) + '\n'
            'CONTEXTO ANTERIOR:\n' + repr(prior_context) + '\n'
            'RESPUESTA ÍNTEGRA:\n' + repr(response_text) + '\n'
            'FUENTE DE LA CITA:\n' + ('usuario' if source_text == user_text else 'respuesta') + '\n'
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
            return 'ambiguous'
        verdict = result['verdict']
        if verdict not in ('supported', 'unsupported', 'ambiguous') or not isinstance(result['reason'], str) or not result['reason'].strip() or not isinstance(result['counterevidence'], str):
            return 'ambiguous'
        if result['counterevidence'] and not any(result['counterevidence'] in t for t in (user_text, response_text, prior_context)):
            return 'ambiguous'
        # Rechazo conservador de una contradicción explícita observada en
        # auditorías reales. No se infiere que el resto de razones sean correctas.
        if indicator == 'CE4' and verdict == 'supported' and 'Impacto estructural declarado: substantial' in interpretation:
            reason = result['reason'].lower()
            if (re.search(r'(?:no (?:hay|existe|presenta)|sin) (?:una? )?(?:deficiencia|dificultad|problema) sustancial', reason)
                    or re.search(r'la estructura es adecuada', reason)):
                verdict = 'ambiguous'
        if verdict == 'supported' and result['counterevidence']:
            return 'ambiguous'
        if audit_log is not None:
            audit_log.append({'indicator': indicator, 'quote': quote, 'interpretation': interpretation,
                              'verdict': verdict, 'reason': result['reason'],
                              'counterevidence': result['counterevidence']})
        return verdict

    return verify_claim
