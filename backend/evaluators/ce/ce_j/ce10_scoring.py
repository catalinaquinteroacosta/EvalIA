"""CE10: puntuación exclusivamente de componentes semánticos verificados."""
LEVELS = {'severe':0,'substantial':1,'minor':2,'none':3}
def score(*, verified, applicable, defect):
    if type(verified) is not bool or type(applicable) is not bool: raise ValueError('Booleanos requeridos')
    if not verified: return {'status':'insufficient_evidence','score':None}
    if not applicable: return {'status':'not_applicable','score':None}
    if defect not in LEVELS: raise ValueError('Defecto inválido')
    return {'status':'scored','score':LEVELS[defect]}
