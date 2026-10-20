"""CE8: extracción no verificada; el modelo NO puntúa."""
import json
from backend.evaluators.semantic.semantic_provider import run_structured_semantic,get_semantic_identity
from .ce8_evidence import validate_ce8_evidence
VERSION='ce8-draft-0.1.0'
SCHEMA={'type':'object','additionalProperties':False,'properties':{
 'analysis_complete':{'type':'boolean'},'full_response_audited':{'type':'boolean'},
 'applicable':{'type':'boolean'}, 'closure_quality':{'type':'string','enum':['complete', 'adequate', 'minimal', 'absent']},
 'claims':{'type':'array','items':{'type':'object','additionalProperties':False,
 'properties':{'source':{'type':'string','enum':['user','response']},'quote':{'type':'string'},'interpretation':{'type':'string'}},
 'required':['source','quote','interpretation']}}},
 'required':['analysis_complete','full_response_audited','applicable','closure_quality','claims']}
def extract_ce8_draft(*,user_text,response_text,prior_context='',model=None,provider=None,semantic_runner=None):
    if not isinstance(user_text,str) or not user_text.strip(): raise ValueError('Usuario ausente')
    if not isinstance(response_text,str) or not response_text.strip(): raise ValueError('Respuesta ausente')
    if not isinstance(prior_context,str): raise ValueError('Contexto inválido')
    prompt=('Cuando corresponde, ¿finaliza con una síntesis, prioridad o siguiente paso identificable?'+'\n'+'Primero establece si un cierre orientador es contextualmente pertinente, con evidencia del usuario o la respuesta. Una despedida no activa CE8. Si el intercambio ya está resuelto y no necesita orientación final, applicable=false. Si es pertinente, examina síntesis, prioridad O siguiente paso, no exige los tres. complete: cierre identificable y contextualizado; adequate: útil con limitación secundaria; minimal: genérico o insuficiente; absent: omitido o contraproducente.'+'\nExtrae componentes semánticos y citas literales, NUNCA puntuaciones. '
       +'REGLA ESTRICTA DE CITAS: toda quote debe copiarse caracter por caracter como una subcadena exacta de la fuente indicada. '
       +'No parafrasees, no corrijas ortografia, no cambies tildes, signos, mayusculas, espacios ni caracteres Unicode, no unas fragmentos separados y no completes palabras omitidas. '
       +'Antes de emitir cada claim, comprueba literalmente que quote aparece dentro de la fuente seleccionada. Si no existe una cita literal valida para una interpretacion, NO generes ese claim. '
       +'Para ausencia de defectos no inventes citas: usa auditoria integral. '
       +'Si no puedes comprobar toda la respuesta, analysis_complete=false. '
       +('CE8: decide applicable unicamente por la necesidad contextual de un cierre orientador, NO por si la respuesta lo cumple. Si el usuario necesita sintesis, prioridad o siguiente paso, applicable=true incluso cuando la respuesta lo omite por completo; en ese caso closure_quality puede ser absent. Si no corresponde cierre orientador, applicable=false y closure_quality=absent. No activar por despedida.' if 8==8 else 'CE6/CE7 son generales y aplicables con respuesta evaluable.')
       +'\nContexto previo: '+json.dumps(prior_context,ensure_ascii=False)+'\nUsuario: '+json.dumps(user_text,ensure_ascii=False)+'\nRespuesta completa: '+json.dumps(response_text,ensure_ascii=False))
    result=(semantic_runner or run_structured_semantic)(prompt=prompt,schema=SCHEMA,model=model,provider=provider)
    if not isinstance(result,dict) or set(result)!=set(SCHEMA['required']): raise ValueError('Borrador incompleto')
    return {'status':'unverified_draft','version':VERSION,'identity':get_semantic_identity(provider=provider,model=model),'extraction':result}
def evaluate_ce8_with_verifier(*,user_text,response_text,extraction,verify_claim,prior_context=''):
    return validate_ce8_evidence(user_text=user_text,response_text=response_text,extraction=extraction,verify_claim=verify_claim,prior_context=prior_context)
