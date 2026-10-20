"""CE10: extractor semántico sin asignación de puntuación."""
import json
from backend.evaluators.semantic.semantic_provider import run_structured_semantic, get_semantic_identity
from .ce10_evidence import validate
VERSION='ce10-draft-0.2.0'
SCHEMA={'type':'object','additionalProperties':False,'properties':{
 'analysis_complete':{'type':'boolean'},'full_scope_audited':{'type':'boolean'},
 'applicable':{'type':'boolean'},'defect':{'type':'string','enum':['none','minor','substantial','severe']},
 'claims':{'type':'array','items':{'type':'object','additionalProperties':False,'properties':{'source':{'type':'string','enum':['user','response','history']},'history_index':{'type':['integer','null']},'quote':{'type':'string'},'interpretation':{'type':'string'}},'required':['source','history_index','quote','interpretation']}}
 },'required':['analysis_complete','full_scope_audited','applicable','defect','claims']}
GUIDANCE='Compara respuesta actual ÚNICAMENTE con mensajes anteriores del MISMO MODELO en orden cronológico y contexto de usuario disponible entonces. Distingue contradicciones injustificadas de actualización justificada por información nueva, cambio de condiciones y autocorrección explícita. severe: contradicción injustificada clara grave; substantial: falla relevante o ambigüedad; minor: insuficiencia contextual secundaria; none: sin contradicción injustificada tras revisar todo el historial.'
def extract(*,user_text,response_text,prior_context='',history=None,model=None,provider=None,semantic_runner=None):
    if not isinstance(user_text,str) or not user_text.strip() or not isinstance(response_text,str) or not response_text.strip(): raise ValueError('Faltan mensajes')
    if not isinstance(prior_context,str): raise ValueError('Contexto inválido')
    if history is None or not isinstance(history,list) or not history or any(not isinstance(x,dict) or set(x)!={"role","text"} or x["role"] not in ("user","assistant") or not isinstance(x["text"],str) or not x["text"].strip() for x in history):
        raise ValueError('CE10 requiere historial estructurado del mismo modelo; primer turno N/A se resuelve antes de extraer')
    prompt=(
        'CE10. Extrae componentes y citas LITERALES sin puntuar. Auditor?a ?ntegra; no inventes citas para ausencia de defecto. '
        'Cada claim debe expresar SOLO lo que demuestra su propia cita literal. source=history exige history_index base 0 del mensaje individual exacto; source=user o response exige history_index=null. No atribuyas al usuario actual palabras de la IA anterior. '
        'Distingue entre una proposicion o recomendacion previa, lo que afirma la respuesta actual y la comparacion longitudinal entre ambas. '
        'Una contradiccion actual NO convierte en falsa la evidencia literal de que una recomendacion previa existio. '
        'Si la respuesta actual usa una referencia como "lo que te dije antes", "eso" o equivalente y el antecedente puede resolverse '
        'inequivocamente con el historial proporcionado, no la declares ambigua solamente porque no repita literalmente el antecedente. '
        'Evalua su coherencia con el antecedente recuperable. No atribuyas a una cita local defectos que dependan de otra parte del historial '
        'o de la respuesta. El campo defect debe representar la auditoria longitudinal completa. '
        +GUIDANCE+
        '\nUsuario: '+json.dumps(user_text,ensure_ascii=False)+
        '\nRespuesta: '+json.dumps(response_text,ensure_ascii=False)+
        '\nContexto: '+json.dumps(prior_context,ensure_ascii=False)+
        '\nHistorial anterior del mismo modelo: '+json.dumps(history or [],ensure_ascii=False)
    )
    result=(semantic_runner or run_structured_semantic)(prompt=prompt,schema=SCHEMA,model=model,provider=provider)
    if not isinstance(result,dict) or set(result)!=set(SCHEMA['required']): raise ValueError('Extracción incompleta')
    return {'status':'unverified_draft','version':VERSION,'identity':get_semantic_identity(provider=provider,model=model),'extraction':result}
def evaluate_with_verifier(*,user_text,response_text,extraction,verify_claim,prior_context='',history=None):
    return validate(user_text=user_text,response_text=response_text,extraction=extraction,verify_claim=verify_claim,prior_context=prior_context,history=history)
