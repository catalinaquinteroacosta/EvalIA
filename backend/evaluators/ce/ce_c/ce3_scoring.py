"""CE3 - puntuación determinista de componentes semánticos verificados.
No invocar directamente con texto ni salida cruda de OpenAI.
"""
class ContractError(ValueError): pass

def score_ce3(*, analysis_complete, semantic_verified, order_impact, applicable=True):
    for key,value in {'analysis_complete':analysis_complete,'semantic_verified':semantic_verified,'applicable':applicable}.items():
        if type(value) is not bool: raise ContractError(f'{key} debe ser booleano')
    if not analysis_complete or not semantic_verified:
        return {'status':'insufficient_evidence','score':None}
    if not applicable:
        raise ContractError('Este indicador es aplicable a respuestas completas')
    if order_impact not in ('clear', 'secondary', 'substantial', 'unintelligible'): raise ContractError('Impacto no validado')
    return {'status':'scored','score':dict(zip(('clear', 'secondary', 'substantial', 'unintelligible'),(3,2,1,0)))[order_impact]}
