"""Verificador independiente CE9/CE10. Fail closed ante duda."""
import json
SCHEMA={'type':'object','additionalProperties':False,'properties':{'verdict':{'type':'string','enum':['supported','unsupported','ambiguous']},'reason':{'type':'string'},'counterevidence':{'type':'string'}},'required':['verdict','reason','counterevidence']}
def build_verifier(*,indicator,user_text,response_text,prior_context='',history=None,semantic_runner,model=None,provider=None,audit_log=None):
    if indicator not in ('CE9','CE10') or not callable(semantic_runner): raise ValueError('Verificador separado obligatorio')
    history_text=json.dumps(history or [],ensure_ascii=False)
    allowed=[user_text,response_text]+([x['text'] for x in history] if indicator=='CE10' and isinstance(history,list) else [])
    def verify_claim(source_text,quote,interpretation):
        if not all(isinstance(x,str) for x in (source_text,quote,interpretation)) or not quote.strip() or quote not in source_text or source_text not in allowed: return 'unsupported'
        prompt=('VERIFICADOR INDEPENDIENTE '+indicator+'. NO PUNTÚES. Revisa críticamente interpretación y evidencia, busca contraevidencia y audita respuesta entera cuando se solicite. '
                'No apruebes por mera existencia de cita. Usa ambiguous si no puedes confirmar TODO. CE9: extensión contextual sin umbral fijo. CE10: solo turnos anteriores del mismo modelo; cambio justificado no contradice. '
                'Devuelve supported solo si plenamente respaldado; counterevidence debe ser cita literal o vacío.\nUsuario: '+repr(user_text)+'\nContexto: '+repr(prior_context)+'\nHistorial: '+history_text+'\nRespuesta: '+repr(response_text)+'\nFuente: '+repr(source_text)+'\nCita: '+repr(quote)+'\nAfirmación: '+repr(interpretation))
        try: r=semantic_runner(prompt=prompt,schema=SCHEMA,model=model,provider=provider)
        except Exception: return 'ambiguous'
        if not isinstance(r,dict) or set(r)!=set(SCHEMA['required']) or r['verdict'] not in ('supported','unsupported','ambiguous') or not isinstance(r['reason'],str) or not r['reason'].strip() or not isinstance(r['counterevidence'],str): return 'ambiguous'
        if r['counterevidence'] and (r['verdict']=='supported' or not any(r['counterevidence'] in t for t in allowed+[prior_context])): return 'ambiguous'
        if audit_log is not None: audit_log.append({'indicator':indicator,'quote':quote,'interpretation':interpretation,**r})
        return r['verdict']
    if indicator == 'CE10':
        def audit_level(proposed_level):
            return audit_ce10_level(
                user_text=user_text,
                response_text=response_text,
                prior_context=prior_context,
                history=history,
                proposed_level=proposed_level,
                semantic_runner=semantic_runner,
                model=model,
                provider=provider,
                audit_log=audit_log)
        verify_claim._ce10_level_auditor = audit_level

    return verify_claim

CE10_LEVEL_AUDIT_SCHEMA={
    'type':'object',
    'additionalProperties':False,
    'properties':{
        'supported_level':{
            'type':'string',
            'enum':['none','minor','substantial','severe']
        },
        'reason':{'type':'string'},
        'counterevidence':{'type':'string'}
    },
    'required':['supported_level','reason','counterevidence']
}


def audit_ce10_level(*,user_text,response_text,prior_context='',history,
                     proposed_level,semantic_runner,model=None,provider=None,
                     audit_log=None):
    """Auditor?a independiente del NIVEL global CE10; no asigna puntaje."""
    if not callable(semantic_runner):
        raise ValueError('Verificador separado obligatorio')

    if proposed_level not in ('none','minor','substantial','severe'):
        raise ValueError('Nivel CE10 inv?lido')

    if not isinstance(history,list) or not history or any(
        not isinstance(x,dict)
        or set(x)!={'role','text'}
        or x['role'] not in ('user','assistant')
        or not isinstance(x['text'],str) or not x['text'].strip()
        for x in history
    ):
        raise ValueError('Historial estructurado CE10 requerido')

    history_text=json.dumps(history,ensure_ascii=False)

    prompt=(
        'AUDITOR?A INDEPENDIENTE GLOBAL CE10. NO PUNT?ES. '
        'Determina qu? NIVEL DE DEFECTO describe mejor la coherencia longitudinal '
        'de la respuesta actual frente ?NICAMENTE a turnos anteriores del MISMO MODELO. '
        'No uses turnos futuros. Distingue contradicci?n injustificada de cambio '
        'justificado por informaci?n nueva, cambio de condiciones o autocorrecci?n expl?cita. '
        'Usa exactamente estas categor?as sem?nticas: '
        'severe = contradicci?n injustificada clara grave; '
        'substantial = falla relevante o ambig?edad que impide una coherencia adecuada; '
        'minor = la coherencia esencial se mantiene pero existe una insuficiencia contextual secundaria; '
        'none = no existe contradicci?n injustificada ni defecto CE10 observable. '
        'No asignes 0/1/2/3. '
        'El nivel propuesto por el extractor es solo una HIP?TESIS y no debes favorecerlo. '
        'Devuelve supported_level con la categor?a que realmente est? mejor respaldaldada. '
        'reason debe explicar la comparaci?n longitudinal. '
        'counterevidence debe contener evidencia literal que vaya CONTRA el nivel elegido, '
        'o cadena vac?a si no existe. '
        '\nUsuario actual: '+repr(user_text)+
        '\nContexto previo disponible: '+repr(prior_context)+
        '\nHistorial anterior del mismo modelo: '+history_text+
        '\nRespuesta actual: '+repr(response_text)+
        '\nNivel propuesto por extractor: '+repr(proposed_level)
    )

    try:
        r=semantic_runner(
            prompt=prompt,
            schema=CE10_LEVEL_AUDIT_SCHEMA,
            model=model,
            provider=provider
        )
    except Exception:
        return None

    if (
        not isinstance(r,dict)
        or set(r)!=set(CE10_LEVEL_AUDIT_SCHEMA['required'])
        or r.get('supported_level') not in ('none','minor','substantial','severe')
        or not isinstance(r.get('reason'),str)
        or not r['reason'].strip()
        or not isinstance(r.get('counterevidence'),str)
    ):
        return None

    if audit_log is not None:
        audit_log.append({
            'indicator':'CE10',
            'audit_type':'global_level',
            'proposed_level':proposed_level,
            **r
        })

    if r['counterevidence']:
        allowed_texts = [
            user_text, response_text, prior_context, *[x['text'] for x in history]
        ]
        if not any(r['counterevidence'] in t for t in allowed_texts):
            return None
        return None
    return r['supported_level']

