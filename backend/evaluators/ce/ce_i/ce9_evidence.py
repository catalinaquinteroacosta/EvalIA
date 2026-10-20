"""CE9: trazabilidad literal y auditoría independiente conservadora."""
import json
from .ce9_scoring import score


def validate(*,user_text,response_text,extraction,verify_claim,prior_context='',history=None):
    if not isinstance(user_text,str) or not user_text.strip() or not isinstance(response_text,str) or not response_text.strip(): raise ValueError('Datos faltantes')
    if not isinstance(prior_context,str) or not callable(verify_claim) or not isinstance(extraction,dict): raise ValueError('Contrato inválido')
    if set(extraction)!={'analysis_complete','full_scope_audited','applicable','defect','claims'}: raise ValueError('Campos inválidos')
    if any(type(extraction[k]) is not bool for k in ('analysis_complete','full_scope_audited','applicable')): raise ValueError('Booleano inválido')
    if not extraction['analysis_complete'] or not extraction['full_scope_audited']: return score(verified=False,applicable=True,defect='none')
    if extraction['defect'] not in ('none','minor','substantial','severe'): raise ValueError('Nivel inválido')
    if not extraction['applicable']: raise ValueError("CE9 requiere evaluación general")
    if False: pass
    history_text=json.dumps(history or [],ensure_ascii=False)
    sources={'user':user_text,'response':response_text}
    claims=extraction['claims']
    if not isinstance(claims,list): raise ValueError('Claims inválidas')
    for claim in claims:
        if not isinstance(claim,dict) or set(claim)!={'source','quote','interpretation'}: raise ValueError('Claim inválida')
        src=claim['source'];quote=claim['quote'];interpretation=claim['interpretation']
        if src not in sources or not isinstance(quote,str) or not quote.strip() or quote not in sources[src] or not isinstance(interpretation,str) or not interpretation.strip(): raise ValueError('Cita/claim inválida')
        scoped=(('CE9 VERIFICACIÓN DE FUENTE USUARIO: comprueba únicamente si el mensaje del usuario expresa esta necesidad o restricción. Que la respuesta la incumpla NO refuta la petición. ' if src=='user' else 'CE9 VERIFICACIÓN DE FUENTE RESPUESTA: comprueba únicamente si la cita de la respuesta expresa esta característica local. ') + 'Proposición: '+interpretation)
        if verify_claim(sources[src],quote,scoped)!='supported': return score(verified=False,applicable=True,defect='none')
    if extraction['defect']!='none' and not claims: return score(verified=False,applicable=True,defect='none')
    from .ce9_provider_bridge import GUIDANCE
    audit='AUDITORÍA COMPLETA CE9. '+GUIDANCE+' Verifica críticamente clasificación defect='+extraction['defect']+'; revisa respuesta COMPLETA, solicitud y contexto. Busca contraevidencia; no asignes puntaje. Usuario: '+repr(user_text)+' Contexto: '+repr(prior_context)+' Historial anterior: '+history_text
    if verify_claim(response_text,response_text,audit)!='supported': return score(verified=False,applicable=True,defect='none')
    return score(verified=True,applicable=True,defect=extraction['defect'])
