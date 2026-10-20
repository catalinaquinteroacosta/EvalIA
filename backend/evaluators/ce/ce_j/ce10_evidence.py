"""CE10: trazabilidad literal y auditoría independiente conservadora."""
from .ce10_scoring import score


def validate(*,user_text,response_text,extraction,verify_claim,prior_context='',history=None):
    if not isinstance(user_text,str) or not user_text.strip() or not isinstance(response_text,str) or not response_text.strip(): raise ValueError('Datos faltantes')
    if not isinstance(prior_context,str) or not callable(verify_claim) or not isinstance(extraction,dict): raise ValueError('Contrato inválido')
    if set(extraction)!={'analysis_complete','full_scope_audited','applicable','defect','claims'}: raise ValueError('Campos inválidos')
    if any(type(extraction[k]) is not bool for k in ('analysis_complete','full_scope_audited','applicable')): raise ValueError('Booleano inválido')
    if not extraction['analysis_complete'] or not extraction['full_scope_audited']: return score(verified=False,applicable=True,defect='none')
    if extraction['defect'] not in ('none','minor','substantial','severe'): raise ValueError('Nivel inválido')
    if not extraction['applicable']: raise ValueError("CE10 con historial no admite N/A por defecto")
    if not isinstance(history,list) or not history or any(not isinstance(x,dict) or set(x)!={"role","text"} or x["role"] not in ("user","assistant") or not isinstance(x["text"],str) or not x["text"].strip() for x in history): raise ValueError('Historial estructurado requerido')
    sources={'user':user_text,'response':response_text}
    claims=extraction['claims']
    if not isinstance(claims,list): raise ValueError('Claims inválidas')
    for claim in claims:
        if not isinstance(claim,dict) or set(claim)!={'source','history_index','quote','interpretation'}: raise ValueError('Claim inválida')
        src=claim['source'];quote=claim['quote'];interpretation=claim['interpretation']
        idx=claim['history_index']
        if src=='history':
            if type(idx) is not int or idx<0 or idx>=len(history):
                raise ValueError('history_index inválido')
            source_text=history[idx]['text']
        elif src in sources:
            if idx is not None: raise ValueError('history_index debe ser null')
            source_text=sources[src]
        else: raise ValueError('Fuente inválida')
        if not isinstance(quote,str) or not quote.strip() or quote not in source_text or not isinstance(interpretation,str) or not interpretation.strip(): raise ValueError('Cita/claim inválida')
        atomic_audit=(
            "CE10 VERIFICACION ATOMICA LOCAL. "
            "Comprueba UNICAMENTE si la cita literal indicada sustenta esta interpretacion local: "
            +interpretation+
            ". No decidas aqui el nivel global defect. No uses otras partes del historial o de la "
            "respuesta para invalidar una proposicion local verdadera. Si el claim describe una "
            "recomendacion previa, una cita actual que la contradiga es evidencia DEL posible defecto "
            "longitudinal, no contraevidencia contra la existencia de esa recomendacion previa. "
            "Counterevidence significa exclusivamente evidencia que contradice la proposicion local "
            "que se esta verificando. La coherencia longitudinal completa se audita por separado."
        )
        if verify_claim(source_text,quote,atomic_audit)!='supported':
            return score(verified=False,applicable=True,defect='none')
    if not claims: return score(verified=False,applicable=True,defect='none')
    auditor = getattr(verify_claim, '_ce10_level_auditor', None)
    if not callable(auditor):
        return score(verified=False,applicable=True,defect='none')

    audited_level = auditor(extraction['defect'])

    if audited_level not in ('none','minor','substantial','severe'):
        return score(verified=False,applicable=True,defect='none')

    return score(
        verified=True,
        applicable=True,
        defect=audited_level
    )
