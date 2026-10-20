"""Puerta de evidencia literal + verificación semántica independiente para CE3."""
from .ce3_scoring import score_ce3,ContractError

def validate_ce3_evidence(*,user_text,response_text,extraction,verify_claim):
    if not isinstance(user_text,str) or not user_text.strip(): raise ContractError('Falta usuario')
    if not isinstance(response_text,str) or not response_text.strip(): raise ContractError('Falta respuesta completa')
    if not isinstance(extraction,dict) or not callable(verify_claim): raise ContractError('Contrato inválido')
    required={'analysis_complete','full_response_audited','applicable','order_impact','claims'}
    if set(extraction)!=required: raise ContractError('Campos inesperados o ausentes')
    for name in ('analysis_complete','full_response_audited','applicable'):
        if type(extraction[name]) is not bool: raise ContractError('Estado inválido')
    if not extraction['analysis_complete'] or not extraction['full_response_audited']:
        return {'status':'insufficient_evidence','score':None}
    if not extraction['applicable']:
        # CE3 is applicable to a complete response. An invalid semantic draft
        # must be reviewed, not converted into N/A or scored.
        return {'status':'insufficient_evidence','score':None, 'reason':'invalid_applicability_draft'}
    if extraction['order_impact'] not in ('clear', 'secondary', 'substantial', 'unintelligible'): raise ContractError('Impacto inválido')
    claims=extraction['claims']
    if not isinstance(claims,list) or not claims: return {'status':'insufficient_evidence','score':None}
    for claim in claims:
        if not isinstance(claim,dict) or set(claim)!={'source','quote','interpretation'}: raise ContractError('Claim inválida')
        source=claim['source'];quote=claim['quote'];interpretation=claim['interpretation']
        if source not in ('user','response'): raise ContractError('Fuente inválida')
        original=user_text if source=='user' else response_text
        if not isinstance(quote,str) or not quote.strip() or quote not in original: raise ContractError('Cita no literal')
        if not isinstance(interpretation,str) or not interpretation.strip(): raise ContractError('Interpretación vacía')
        verdict=verify_claim(original,quote,(
            'CE3 VERIFICACION ATOMICA: decide SOLO si la cita indicada respalda la '
            'interpretacion local siguiente: '+interpretation+
            '. No juzgues aqui el nivel global de orden ni la gravedad total. '
            'El resto de la respuesta solo es contraevidencia si contradice '
            'directamente esta proposicion local. Un defecto posterior distinto '
            'no vuelve ambigua una afirmacion verdadera sobre esta cita. '
            'La gravedad global se verifica despues mediante auditoria integral.'
        ))
        if verdict not in ('supported','unsupported','ambiguous'): raise ContractError('Veredicto inválido')
        if verdict!='supported': return {'status':'insufficient_evidence','score':None}
    # Auditoría integral de dimensión y ausencia: la evidencia aislada no prueba ausencia de defectos.
    verdict=verify_claim(response_text,response_text,'CE3 auditoría integral: evalúa TODA la respuesta respecto a la necesidad del usuario. Verifica orden comprensible de ideas y transiciones funcionales (no exijas conectores explícitos). Impacto declarado: '+str(extraction['order_impact'])+'. clear: orden claro sin defectos relevantes; secondary: defecto menor con comprensión conservada; substantial: desorden que dificulta significativamente la comprensión; unintelligible: el desorden impide comprender la respuesta. Confirma el impacto concreto, busca contraejemplos y no puntúes.')
    if verdict!='supported': return {'status':'insufficient_evidence','score':None}
    return score_ce3(analysis_complete=True,semantic_verified=True,applicable=True,order_impact=extraction['order_impact'])
