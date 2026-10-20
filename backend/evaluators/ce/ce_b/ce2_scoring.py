"""CE2: puntuación determinista SOLO de hechos semánticos previamente verificados.

Contrato basado en CE2: suficiencia sin omisiones esenciales ni sobrecarga.
La extracción semántica OpenAI y sus validadores son un paso independiente
PENDIENTE. No utilizar este módulo directamente con salida cruda del modelo.
"""

class CE2ContractError(ValueError):
    pass


def score_ce2(*, analysis_complete, need_coverage, overload, secondary_defect,
              semantic_verified):
    """Recibe dictamen semántico validado, nunca inferencias de longitud.

    need_coverage: absent, generic, essential_met
    overload: none, secondary, obstructive
    secondary_defect: bool, defecto menor de precisión/adaptación verificado
    semantic_verified: bool, validación contextual y de evidencias completada
    """
    for label, value in [('analysis_complete', analysis_complete),
                         ('secondary_defect', secondary_defect),
                         ('semantic_verified', semantic_verified)]:
        if type(value) is not bool:
            raise CE2ContractError(f'{label} debe ser booleano.')
    if not analysis_complete or not semantic_verified:
        return {'status': 'insufficient_evidence', 'score': None}
    if need_coverage not in {'absent', 'generic', 'essential_met'}:
        raise CE2ContractError('Cobertura de necesidad no validada.')
    if overload not in {'none', 'secondary', 'obstructive'}:
        raise CE2ContractError('Sobrecarga no validada.')
    # La escala sigue el anclaje oficial. Los cruces con múltiples defectos
    # se dejan para adjudicación experta, no se resuelven por suposición.
    if need_coverage == 'absent':
        if overload != 'none' or secondary_defect:
            return {'status': 'requires_adjudication', 'score': None}
        return {'status': 'scored', 'score': 0}
    if need_coverage == 'generic':
        if overload != 'none' or secondary_defect:
            return {'status': 'requires_adjudication', 'score': None}
        return {'status': 'scored', 'score': 1}
    if overload == 'obstructive':
        return {'status': 'requires_adjudication', 'score': None}
    if overload == 'secondary' or secondary_defect:
        return {'status': 'scored', 'score': 2}
    return {'status': 'scored', 'score': 3}
