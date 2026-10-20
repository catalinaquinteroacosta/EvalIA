"""CE4 - puntuación determinista de componentes semánticos verificados.
No invocar directamente con texto ni salida cruda de OpenAI.
"""
class ContractError(ValueError): pass

def score_ce4(*, analysis_complete, semantic_verified, structure_impact, applicable=True):
    for key,value in {'analysis_complete':analysis_complete,'semantic_verified':semantic_verified,'applicable':applicable}.items():
        if type(value) is not bool: raise ContractError(f'{key} debe ser booleano')
    if not analysis_complete or not semantic_verified:
        return {'status':'insufficient_evidence','score':None}
    if not applicable:
        return {"status":"not_applicable","score":None}
    if structure_impact not in ('functional', 'secondary', 'substantial', 'unusable'): raise ContractError('Impacto no validado')
    return {'status':'scored','score':dict(zip(('functional', 'secondary', 'substantial', 'unusable'),(3,2,1,0)))[structure_impact]}
