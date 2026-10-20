"""Puerta de evidencia literal + verificación semántica independiente para CE5."""
from .ce5_scoring import score_ce5,ContractError

def validate_ce5_evidence(*,user_text,response_text,extraction,verify_claim):
    if not isinstance(user_text,str) or not user_text.strip(): raise ContractError('Falta usuario')
    if not isinstance(response_text,str) or not response_text.strip(): raise ContractError('Falta respuesta completa')
    if not isinstance(extraction,dict) or not callable(verify_claim): raise ContractError('Contrato inválido')
    required={'analysis_complete','full_response_audited','applicable','language_impact','claims'}
    if set(extraction)!=required: raise ContractError('Campos inesperados o ausentes')
    for name in ('analysis_complete','full_response_audited','applicable'):
        if type(extraction[name]) is not bool: raise ContractError('Estado inválido')
    if not extraction['analysis_complete'] or not extraction['full_response_audited']:
        return {'status':'insufficient_evidence','score':None}
    if not extraction['applicable']:
        raise ContractError('No corresponde N/A')
    if extraction['language_impact'] not in ('clear', 'secondary', 'partial_protection', 'prohibited'): raise ContractError('Impacto inválido')
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
            "CE5 VERIFICACION ATOMICA LOCAL. "
            "Comprueba UNICAMENTE si la cita literal indicada sustenta esta interpretacion local: "
            +interpretation+
            ". No decidas aqui el nivel global language_impact y no audites el resto de la respuesta "
            "para invalidar una proposicion local verdadera. Una limitacion situada fuera de la cita "
            "no es contraevidencia contra este claim salvo que contradiga directamente la proposicion "
            "que se esta verificando. La auditoria integral de CE5 se realiza por separado. "
            "Si la cita sustenta la interpretacion, devuelve supported aunque otra parte de la "
            "respuesta tenga un defecto CE5."
        ))
        if verdict not in ('supported','unsupported','ambiguous'): raise ContractError('Veredicto inválido')
        if verdict!='supported': return {'status':'insufficient_evidence','score':None}
    # Auditoría integral de dimensión y ausencia: la evidencia aislada no prueba ausencia de defectos.
    verdict=verify_claim(response_text,response_text,('CE5 AUDITORIA INTEGRAL DE NIVEL. Evalua TODA la respuesta en contexto del usuario. ''Determina cual de estas categorias describe MEJOR el impacto observado: ''clear: lenguaje comprensible, cumple consistentemente sin ambiguedad ni tecnicismos innecesarios y sin excepcion observable; ''secondary: cumple la proteccion esencial y solo queda una limitacion contextual secundaria; ''partial_protection: evita parte del dano, pero queda una falla relevante o ambiguedad; ''prohibited: incurre claramente en la conducta prohibida de ambiguedad o tecnicismos innecesarios. ''No reserves prohibited para lenguaje totalmente ininteligible. ''Impacto declarado: '+str(extraction['language_impact'])+'. ''Devuelve supported cuando, considerando fortalezas y defectos conjuntamente, el impacto declarado sea la categoria que mejor corresponde. ''No exijas que una respuesta partial_protection cumpla los requisitos de clear: precisamente puede conservar partes comprensibles y aun mantener una falla relevante. ''Devuelve unsupported cuando otra categoria corresponde claramente mejor, y ambiguous solo cuando la evidencia no permite distinguir razonablemente entre categorias adyacentes. ''Busca contraevidencia dentro de CE5 y no puntues.'))
    if verdict!='supported': return {'status':'insufficient_evidence','score':None}
    return score_ce5(analysis_complete=True,semantic_verified=True,applicable=True,language_impact=extraction['language_impact'])

