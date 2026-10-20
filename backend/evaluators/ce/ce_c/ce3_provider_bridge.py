"""Borrador semántico CE3; NUNCA se considera verificado ni asigna puntajes."""
import json
from backend.evaluators.semantic.semantic_provider import run_structured_semantic,get_semantic_identity
from .ce3_evidence import validate_ce3_evidence
VERSION='ce3-draft-0.1.0'
SCHEMA={'type':'object','additionalProperties':False,'properties':{
    'analysis_complete':{'type':'boolean'},'full_response_audited':{'type':'boolean'},
    'applicable':{'type':'boolean'},'order_impact':{'type':'string','enum':['clear', 'secondary', 'substantial', 'unintelligible']},
    'claims':{'type':'array','items':{'type':'object','additionalProperties':False,
       'properties':{'source':{'type':'string','enum':['user','response']},'quote':{'type':'string'},'interpretation':{'type':'string'}},
       'required':['source','quote','interpretation']}}},
 'required':['analysis_complete','full_response_audited','applicable','order_impact','claims']}
def extract_ce3_draft(*,user_text,response_text,prior_context='',model=None,provider=None,semantic_runner=None):
    if not isinstance(user_text,str) or not user_text.strip(): raise ValueError('Falta usuario')
    if not isinstance(response_text,str) or not response_text.strip(): raise ValueError('Falta respuesta íntegra')
    if not isinstance(prior_context,str): raise ValueError('Contexto inválido')
    prompt=('¿Las ideas aparecen en un orden comprensible y con transiciones claras?'+'\nExtrae componentes semánticos y evidencia literal, NO puntúes. '
      +'El orden es evaluable incluso en una respuesta breve sin conectores: marca applicable=true para respuestas completas. No exigir conectores literales, listas ni párrafos.'+' La gravedad debe depender del efecto real en comprensión/uso, no del mero conteo de rasgos. '
      +'Las citas deben ser subcadenas exactas de la fuente correcta. La ausencia de defectos requiere auditar '
      +'la respuesta completa; ante duda marca analysis_complete=false. No inventes citas para ausencias.\n'
      +'Contexto: '+json.dumps(prior_context,ensure_ascii=False)+'\nUsuario: '+json.dumps(user_text,ensure_ascii=False)
      +'\nRespuesta: '+json.dumps(response_text,ensure_ascii=False))
    result=(semantic_runner or run_structured_semantic)(prompt=prompt,schema=SCHEMA,model=model,provider=provider)
    if not isinstance(result,dict) or set(result)!=set(SCHEMA['required']): raise ValueError('Borrador incompleto')
    return {'status':'unverified_draft','version':VERSION,'identity':get_semantic_identity(provider=provider,model=model),'extraction':result}
def evaluate_ce3_with_verifier(*,user_text,response_text,extraction,verify_claim):
    return validate_ce3_evidence(user_text=user_text,response_text=response_text,extraction=extraction,verify_claim=verify_claim)
