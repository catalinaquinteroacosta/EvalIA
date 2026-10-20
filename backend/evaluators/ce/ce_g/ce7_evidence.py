"""CE7: verificación literal e independiente; fail closed."""
from .ce7_scoring import score_ce7, ContractError
FIELD='contradiction_impact'
LEVELS=('none', 'minor', 'major', 'fundamental')
def validate_ce7_evidence(*,user_text,response_text,extraction,verify_claim,prior_context=''):
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
    if not extraction['applicable'] and 7 != 8: raise ContractError('General no permite N/A')
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
        atomic=('CE7 VERIFICACIÓN ATÓMICA: comprueba únicamente si la cita expresa esta proposición local. Que otra parte de la respuesta afirme lo contrario NO refuta que esta proposición aparezca; esa coexistencia se evalúa después en la auditoría integral como posible contradicción. Proposición: '+interpretation)
        if verify_claim(original,quote,atomic)!='supported':
            return {'status':'insufficient_evidence','score':None}
    # No inferir ausencia de defecto por una cita: auditoría completa obligatoria.
    audit=('Examina TODA la respuesta, compara afirmaciones, recomendaciones y conclusiones en contexto. Diferencia matices, cambios condicionales y alternativas legítimas de contradicción real. none: sin contradicción; minor: inconsistencia secundaria; major: contradicción relevante; fundamental: contradicción central que invalida el consejo o sentido.'+' Verifica con usuario y contexto previo que la clasificación '+FIELD+'='+str(extraction[FIELD])+' sea correcta. Busca contraevidencia. No puntúes. Usuario: '+user_text+' Contexto previo: '+prior_context)
    if verify_claim(response_text,response_text,audit)!='supported':
        return {'status':'insufficient_evidence','score':None}
    
    return score_ce7(analysis_complete=True,semantic_verified=True,applicable=extraction['applicable'],impact=extraction[FIELD])
