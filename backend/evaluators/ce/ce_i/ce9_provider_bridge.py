"""CE9: extractor semántico sin asignación de puntuación."""
import json
from backend.evaluators.semantic.semantic_provider import run_structured_semantic, get_semantic_identity
from .ce9_evidence import validate
VERSION='ce9-draft-0.2.0'
SCHEMA={'type':'object','additionalProperties':False,'properties':{
 'analysis_complete':{'type':'boolean'},'full_scope_audited':{'type':'boolean'},
 'applicable':{'type':'boolean'},'defect':{'type':'string','enum':['none','minor','substantial','severe']},
 'claims':{'type':'array','maxItems':3,'items':{'type':'object','additionalProperties':False,'properties':{'source':{'type':'string','enum':['user','response']},'quote':{'type':'string'},'interpretation':{'type':'string'}},'required':['source','quote','interpretation']}}
 },'required':['analysis_complete','full_scope_audited','applicable','defect','claims']}
GUIDANCE='Examina extensión, formato y densidad para chat según solicitud y complejidad. NO uses umbrales de palabras; una respuesta extensa bien organizada y solicitada puede no tener defectos. Considera severidad conjunta de dificultad real de procesamiento; no confundas con precisión temática, estructura como indicador separado ni redundancia. severe: respuesta prácticamente improcesable; substantial: dificultad considerable; minor: dificultad secundaria; none: totalmente procesable.'
def extract(*,user_text,response_text,prior_context='',history=None,model=None,provider=None,semantic_runner=None):
    if not isinstance(user_text,str) or not user_text.strip() or not isinstance(response_text,str) or not response_text.strip(): raise ValueError('Faltan mensajes')
    if not isinstance(prior_context,str): raise ValueError('Contexto inválido')
    if False:
        pass
    prompt='CE9. Selecciona como máximo 3 afirmaciones probatorias NO redundantes y de mayor valor; la auditoría integral verificará el conjunto. Extrae componentes y citas LITERALES sin puntuar. Auditoría íntegra; no inventes citas para ausencia de defecto. '+GUIDANCE+'\nUsuario: '+json.dumps(user_text,ensure_ascii=False)+'\nRespuesta: '+json.dumps(response_text,ensure_ascii=False)+'\nContexto: '+json.dumps(prior_context,ensure_ascii=False)+'\nHistorial anterior del mismo modelo: '+json.dumps(history or [],ensure_ascii=False)
    result=(semantic_runner or run_structured_semantic)(prompt=prompt,schema=SCHEMA,model=model,provider=provider)
    if not isinstance(result,dict) or set(result)!=set(SCHEMA['required']): raise ValueError('Extracción incompleta')
    return {'status':'unverified_draft','version':VERSION,'identity':get_semantic_identity(provider=provider,model=model),'extraction':result}
def evaluate_with_verifier(*,user_text,response_text,extraction,verify_claim,prior_context='',history=None):
    return validate(user_text=user_text,response_text=response_text,extraction=extraction,verify_claim=verify_claim,prior_context=prior_context,history=history)
