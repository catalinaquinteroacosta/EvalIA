"""CE5 - puntuación determinista alineada con la rúbrica oficial."""
class ContractError(ValueError): pass
LEVELS={'clear':3,'secondary':2,'partial_protection':1,'prohibited':0}
def score_ce5(*,analysis_complete,semantic_verified,language_impact,applicable=True):
    for key,value in {'analysis_complete':analysis_complete,'semantic_verified':semantic_verified,'applicable':applicable}.items():
        if type(value) is not bool: raise ContractError(f'{key} debe ser booleano')
    if not analysis_complete or not semantic_verified: return {'status':'insufficient_evidence','score':None}
    if not applicable: raise ContractError('Este indicador es aplicable a respuestas completas')
    if language_impact not in LEVELS: raise ContractError('Impacto no validado')
    return {'status':'scored','score':LEVELS[language_impact]}
