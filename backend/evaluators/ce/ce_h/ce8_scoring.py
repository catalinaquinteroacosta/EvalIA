"""CE8: regla determinista; entrada exclusivamente semántica verificada."""
class ContractError(ValueError): pass
LEVELS={'complete': 3, 'adequate': 2, 'minimal': 1, 'absent': 0}
def score_ce8(*,analysis_complete,semantic_verified,applicable,impact):
    for name,val in {'analysis_complete':analysis_complete,'semantic_verified':semantic_verified,'applicable':applicable}.items():
        if type(val) is not bool: raise ContractError(name+' inválido')
    if not analysis_complete or not semantic_verified: return {'status':'insufficient_evidence','score':None}
    if not applicable:
        return {"status":"not_applicable","score":None}
    if impact not in LEVELS: raise ContractError('Impacto no validado')
    return {'status':'scored','score':LEVELS[impact]}
