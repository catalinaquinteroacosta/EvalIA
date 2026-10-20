"""CE6: verificación literal e independiente; fail closed."""
from .ce6_scoring import score_ce6, ContractError
FIELD='redundancy_impact'
LEVELS=('none', 'minor', 'major', 'pervasive')
def validate_ce6_evidence(*,user_text,response_text,extraction,verify_claim,prior_context=''):
    if not isinstance(user_text,str) or not user_text.strip(): raise ContractError('Usuario ausente')
    if not isinstance(response_text,str) or not response_text.strip(): raise ContractError('Respuesta ausente')
    if not isinstance(prior_context,str): raise ContractError('Contexto inválido')
    if not callable(verify_claim) or not isinstance(extraction,dict): raise ContractError('Contrato inválido')
    required={'analysis_complete','full_response_audited','applicable',FIELD,'claims'}
    if set(extraction)!=required: raise ContractError('Campos incorrectos')
    for key in ('analysis_complete','full_response_audited','applicable'):
        if type(extraction[key]) is not bool: raise ContractError(key+' no booleano')
    if not extraction['analysis_complete'] or not extraction['full_response_audited']:
        return {'status':'insufficient_evidence','score':None}
    if extraction[FIELD] not in LEVELS: raise ContractError('Impacto desconocido')
    if not extraction['applicable'] and 6 != 8: raise ContractError('General no permite N/A')
    if not extraction['applicable'] and extraction[FIELD]!='absent': raise ContractError('N/A requiere impacto neutro absent')
    claims=extraction['claims']
    if not isinstance(claims,list): raise ContractError('Claims inválidas')
    for claim in claims:
        if not isinstance(claim,dict) or set(claim)!={'source','quote','interpretation'}: raise ContractError('Claim inválida')
        source=claim['source']; quote=claim['quote']; interpretation=claim['interpretation']
        if source not in ('user','response'): raise ContractError('Fuente inválida')
        original={'user':user_text,'response':response_text,'context':prior_context}[source]
        if not isinstance(quote,str) or not quote.strip() or quote not in original: raise ContractError('Cita no literal')
        if not isinstance(interpretation,str) or not interpretation.strip(): raise ContractError('Interpretación inválida')
        if verify_claim(original,quote,interpretation)!='supported':
            return {'status':'insufficient_evidence','score':None}
    # No inferir ausencia de defecto por una cita: auditoría completa obligatoria.
    audit=('Examina TODA la respuesta. Diferencia reiteración útil (énfasis, seguridad, claridad) de repetición sin significado adicional. none: directa sin redundancia inútil; minor: defecto secundario; major: redundancia relevante; pervasive: redundancia dominante que perjudica gravemente la función.'+' Verifica con usuario y contexto previo que la clasificación '+FIELD+'='+str(extraction[FIELD])+' sea correcta. Busca contraevidencia. No puntúes. Usuario: '+user_text+' Contexto previo: '+prior_context)
    if verify_claim(response_text,response_text,audit)!='supported':
        return {'status':'insufficient_evidence','score':None}
    
    return score_ce6(analysis_complete=True,semantic_verified=True,applicable=extraction['applicable'],impact=extraction[FIELD])
