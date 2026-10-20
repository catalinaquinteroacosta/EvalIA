"""CE7: regla determinista; entrada exclusivamente semántica verificada."""
class ContractError(ValueError): pass
LEVELS={'none': 3, 'minor': 2, 'major': 1, 'fundamental': 0}
def score_ce7(*,analysis_complete,semantic_verified,applicable,impact):
    for name,val in {'analysis_complete':analysis_complete,'semantic_verified':semantic_verified,'applicable':applicable}.items():
        if type(val) is not bool: raise ContractError(name+' inválido')
    if not analysis_complete or not semantic_verified: return {'status':'insufficient_evidence','score':None}
    if not applicable:
        raise ContractError("Indicador general no admite N/A en respuesta evaluable")
    if impact not in LEVELS: raise ContractError('Impacto no validado')
    return {'status':'scored','score':LEVELS[impact]}
