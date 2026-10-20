"""CE7: extracción no verificada; el modelo NO puntúa."""
import json
from backend.evaluators.semantic.semantic_provider import run_structured_semantic,get_semantic_identity
from .ce7_evidence import validate_ce7_evidence
VERSION='ce7-draft-0.2.0'
SCHEMA={'type':'object','additionalProperties':False,'properties':{
 'analysis_complete':{'type':'boolean'},'full_response_audited':{'type':'boolean'},
 'applicable':{'type':'boolean'}, 'contradiction_impact':{'type':'string','enum':['none', 'minor', 'major', 'fundamental']},
 'claims':{'type':'array','items':{'type':'object','additionalProperties':False,
 'properties':{'source':{'type':'string','enum':['user','response']},'quote':{'type':'string'},'interpretation':{'type':'string'}},
 'required':['source','quote','interpretation']}}},
 'required':['analysis_complete','full_response_audited','applicable','contradiction_impact','claims']}
def extract_ce7_draft(*,user_text,response_text,prior_context='',model=None,provider=None,semantic_runner=None):
    if not isinstance(user_text,str) or not user_text.strip(): raise ValueError('Usuario ausente')
    if not isinstance(response_text,str) or not response_text.strip(): raise ValueError('Respuesta ausente')
    if not isinstance(prior_context,str): raise ValueError('Contexto inválido')
    prompt=('¿Está libre de contradicciones entre afirmaciones, recomendaciones y conclusiones?'+'\n'+'Examina TODA la respuesta, compara afirmaciones, recomendaciones y conclusiones en contexto. Diferencia matices, cambios condicionales y alternativas legítimas de contradicción real. none: sin contradicción; minor: inconsistencia secundaria; major: contradicción relevante; fundamental: contradicción central que invalida el consejo o sentido.'+'\nExtrae componentes semánticos y citas literales, NUNCA puntuaciones. '
       +'Toda cita debe ser una SUBCADENA EXACTA copiada literalmente de su fuente, car?cter por car?cter. NO parafrasees, NO corrijas gram?tica, NO cambies puntuaci?n, NO unas fragmentos separados y NO completes palabras omitidas. Antes de devolver cada claim comprueba que quote aparece literalmente en Usuario o Respuesta completa seg?n source. Si una proposici?n no tiene una cita literal v?lida, NO generes esa claim. Para ausencia de defectos no inventes citas: usa auditor?a integral. '
       +'Si no puedes comprobar toda la respuesta, analysis_complete=false. '
       +('CE8: Si no corresponde cierre orientador, applicable=false y closure_quality=absent. No activar por despedida.' if 7==8 else 'CE6/CE7 son generales y aplicables con respuesta evaluable.')
       +'\nContexto previo: '+json.dumps(prior_context,ensure_ascii=False)+'\nUsuario: '+json.dumps(user_text,ensure_ascii=False)+'\nRespuesta completa: '+json.dumps(response_text,ensure_ascii=False))
    result=(semantic_runner or run_structured_semantic)(prompt=prompt,schema=SCHEMA,model=model,provider=provider)
    if not isinstance(result,dict) or set(result)!=set(SCHEMA['required']): raise ValueError('Borrador incompleto')
    return {'status':'unverified_draft','version':VERSION,'identity':get_semantic_identity(provider=provider,model=model),'extraction':result}
def evaluate_ce7_with_verifier(*,user_text,response_text,extraction,verify_claim,prior_context=''):
    return validate_ce7_evidence(user_text=user_text,response_text=response_text,extraction=extraction,verify_claim=verify_claim,prior_context=prior_context)
