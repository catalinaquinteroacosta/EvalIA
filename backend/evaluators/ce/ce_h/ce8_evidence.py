"""CE8: verificación literal e independiente; fail closed."""
from .ce8_scoring import score_ce8, ContractError
FIELD='closure_quality'
LEVELS=('complete', 'adequate', 'minimal', 'absent')
def validate_ce8_evidence(*,user_text,response_text,extraction,verify_claim,prior_context=''):
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
    # Auditoria global EXCLUSIVA de calidad del cierre.
    # La aplicabilidad se verifica por separado inmediatamente despues.
    quality_audit = (
        'CE8 AUDITORIA EXCLUSIVA DE CALIDAD DEL CIERRE. '
        'Evalua TODA la respuesta respecto a closure_quality='
        + str(extraction[FIELD]) + '. '
        'En esta auditoria NO decidas si CE8 aplica o no aplica: toma la '
        'aplicabilidad declarada solo como condicion para juzgar la calidad. '
        'La aplicabilidad se verifica independientemente en otra auditoria. '
        'Evalua exclusivamente si la respuesta ofrece sintesis, prioridad O '
        'siguiente paso identificable cuando corresponde evaluar el cierre. '
        'No exige los tres. '
        'complete: cierre identificable, contextualizado y plenamente util; '
        'adequate: cierre util con una limitacion secundaria; '
        'minimal: cierre generico, debil o insuficiente que ofrece orientacion '
        'minima pero no una prioridad o siguiente paso suficientemente util; '
        'absent: cierre orientador omitido o contraproducente. '
        'NO uses dudas sobre la necesidad contextual del cierre como '
        'contraevidencia de closure_quality; eso pertenece exclusivamente a '
        'la auditoria de aplicabilidad. '
        'Determina si la categoria declarada describe MEJOR la respuesta '
        'completa frente a las categorias adyacentes. Busca contraevidencia '
        'SOLO sobre la calidad del cierre y no puntues.'
    )
    if verify_claim(response_text, response_text, quality_audit) != 'supported':
        return {'status':'insufficient_evidence','score':None}

    applicability_audit = (
        'CE8 AUDITORIA EXCLUSIVA DE APLICABILIDAD. '
        'Verifica independientemente applicable=' + str(extraction['applicable']) + '. '
        'Decide SOLO si, por la necesidad del usuario y el estado del intercambio, '
        'corresponde evaluar un cierre orientador (sintesis, prioridad O siguiente paso). '
        'La aplicabilidad NO depende de que la respuesta haya cumplido ese cierre. '
        'Una respuesta puede ser applicable=True y closure_quality=absent precisamente '
        'porque el cierre era necesario y fue omitido. '
        'NO uses como razon para applicable=False que la respuesta sea generica, '
        'insuficiente, no priorice, no recomiende o no ofrezca un siguiente paso: '
        'eso pertenece a closure_quality. Una despedida por si sola no activa CE8. '
        'Si el usuario declara que ya resolvio lo que necesitaba y no quiere '
        'orientacion ni siguiente paso, puede corresponder applicable=False. '
        'Evalua usuario y contexto previo; no puntues.'
    )
    if verify_claim(
        user_text+'\n'+prior_context+'\n'+response_text,
        response_text,
        applicability_audit,
    ) != 'supported':
        return {'status':'insufficient_evidence','score':None}
    return score_ce8(analysis_complete=True,semantic_verified=True,applicable=extraction['applicable'],impact=extraction[FIELD])
