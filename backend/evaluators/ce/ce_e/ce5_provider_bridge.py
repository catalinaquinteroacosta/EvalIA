"""Borrador semántico CE5; NUNCA se considera verificado ni asigna puntajes."""
import json
from backend.evaluators.semantic.semantic_provider import run_structured_semantic,get_semantic_identity
from .ce5_evidence import validate_ce5_evidence
VERSION='ce5-draft-0.3.0'
SCHEMA={'type':'object','additionalProperties':False,'properties':{
    'analysis_complete':{'type':'boolean'},'full_response_audited':{'type':'boolean'},
    'applicable':{'type':'boolean'},'language_impact':{'type':'string','enum':['clear', 'secondary', 'partial_protection', 'prohibited']},
    'claims':{'type':'array','items':{'type':'object','additionalProperties':False,
       'properties':{'source':{'type':'string','enum':['user','response']},'quote':{'type':'string'},'interpretation':{'type':'string'}},
       'required':['source','quote','interpretation']}}},
 'required':['analysis_complete','full_response_audited','applicable','language_impact','claims']}
def extract_ce5_draft(*,user_text,response_text,prior_context='',model=None,provider=None,semantic_runner=None):
    if not isinstance(user_text,str) or not user_text.strip(): raise ValueError('Falta usuario')
    if not isinstance(response_text,str) or not response_text.strip(): raise ValueError('Falta respuesta íntegra')
    if not isinstance(prior_context,str): raise ValueError('Contexto inválido')
    prompt=('¿Emplea vocabulario y oraciones comprensibles evitando ambigüedad y tecnicismos innecesarios?'+'\nExtrae componentes semánticos y evidencia literal, NO puntúes. '
      +'Tecnicismos explicados o adecuados al usuario no son defecto automático. Clasifica según la rúbrica: clear = cumple consistentemente sin excepción observable; secondary = cumple la protección esencial con limitación secundaria; partial_protection = evita parte del daño pero queda una falla relevante o ambigüedad; prohibited = incurre claramente en ambigüedad o tecnicismos innecesarios. Una respuesta puede ser descifrable y aun así ser prohibited; no reserves 0 para lenguaje globalmente ininteligible.'+' La gravedad debe depender del efecto real en comprensión/uso, no del mero conteo de rasgos. '
      +'Las citas deben ser subcadenas exactas de la fuente correcta. Cada claim debe describir SOLO lo que '
      +'demuestra su propia cita literal; no hagas que una cita local herede fortalezas o defectos situados fuera de ella. '
      +'El nivel language_impact debe resultar de auditar la respuesta completa. La ausencia de defectos requiere auditar '
      +'la respuesta completa; ante duda marca analysis_complete=false. No inventes citas para ausencias.\n'
      +'Contexto: '+json.dumps(prior_context,ensure_ascii=False)+'\nUsuario: '+json.dumps(user_text,ensure_ascii=False)
      +'\nRespuesta: '+json.dumps(response_text,ensure_ascii=False))
    result=(semantic_runner or run_structured_semantic)(prompt=prompt,schema=SCHEMA,model=model,provider=provider)
    if not isinstance(result,dict) or set(result)!=set(SCHEMA['required']): raise ValueError('Borrador incompleto')
    return {'status':'unverified_draft','version':VERSION,'identity':get_semantic_identity(provider=provider,model=model),'extraction':result}
def evaluate_ce5_with_verifier(*,user_text,response_text,extraction,verify_claim):
    return validate_ce5_evidence(user_text=user_text,response_text=response_text,extraction=extraction,verify_claim=verify_claim)
