"""CE6: extracción no verificada; el modelo NO puntúa."""
import json
from backend.evaluators.semantic.semantic_provider import run_structured_semantic,get_semantic_identity
from .ce6_evidence import validate_ce6_evidence
VERSION='ce6-draft-0.2.0'
SCHEMA={'type':'object','additionalProperties':False,'properties':{
 'analysis_complete':{'type':'boolean'},'full_response_audited':{'type':'boolean'},
 'applicable':{'type':'boolean'}, 'redundancy_impact':{'type':'string','enum':['none', 'minor', 'major', 'pervasive']},
 'claims':{'type':'array','maxItems':3,'items':{'type':'object','additionalProperties':False,
 'properties':{'source':{'type':'string','enum':['user','response']},'quote':{'type':'string'},'interpretation':{'type':'string'}},
 'required':['source','quote','interpretation']}}},
 'required':['analysis_complete','full_response_audited','applicable','redundancy_impact','claims']}
def extract_ce6_draft(*,user_text,response_text,prior_context='',model=None,provider=None,semantic_runner=None):
    if not isinstance(user_text,str) or not user_text.strip(): raise ValueError('Usuario ausente')
    if not isinstance(response_text,str) or not response_text.strip(): raise ValueError('Respuesta ausente')
    if not isinstance(prior_context,str): raise ValueError('Contexto inválido')
    prompt=('¿Expresa las ideas directamente y evita redundancias sin significado adicional?'+'\n'+'Examina TODA la respuesta. Diferencia reiteración útil (énfasis, seguridad, claridad) de repetición sin significado adicional. none: directa sin redundancia inútil; minor: defecto secundario; major: redundancia relevante; pervasive: redundancia dominante que perjudica gravemente la función.'+'\nExtrae componentes semánticos y citas literales, NUNCA puntuaciones. '
       +'Toda cita debe ser subcadena exacta de su fuente. Para ausencia de defectos no inventes citas: usa auditoría integral. '
       +'Selecciona como máximo 3 afirmaciones probatorias NO redundantes y de mayor valor; la auditoría integral verificará el conjunto. Si no puedes comprobar toda la respuesta, analysis_complete=false. '
       +('CE8: Si no corresponde cierre orientador, applicable=false y closure_quality=absent. No activar por despedida.' if 6==8 else 'CE6/CE7 son generales y aplicables con respuesta evaluable.')
       +'\nContexto previo: '+json.dumps(prior_context,ensure_ascii=False)+'\nUsuario: '+json.dumps(user_text,ensure_ascii=False)+'\nRespuesta completa: '+json.dumps(response_text,ensure_ascii=False))
    result=(semantic_runner or run_structured_semantic)(prompt=prompt,schema=SCHEMA,model=model,provider=provider)
    if not isinstance(result,dict) or set(result)!=set(SCHEMA['required']): raise ValueError('Borrador incompleto')
    return {'status':'unverified_draft','version':VERSION,'identity':get_semantic_identity(provider=provider,model=model),'extraction':result}
def evaluate_ce6_with_verifier(*,user_text,response_text,extraction,verify_claim,prior_context=''):
    return validate_ce6_evidence(user_text=user_text,response_text=response_text,extraction=extraction,verify_claim=verify_claim,prior_context=prior_context)
