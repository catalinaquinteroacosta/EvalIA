"""Puente CE2 al proveedor compartido. NO puntúa ni valida afirmaciones.

El resultado es un borrador semántico: no puede enviarse directamente al scorer.
La validación contextual independiente queda obligatoria.
"""
import json
from backend.evaluators.semantic.semantic_provider import run_structured_semantic, get_semantic_identity

VERSION = 'ce2-bridge-0.1.0'
SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'properties': {
        'analysis_complete': {'type':'boolean'},
        'full_response_audited': {'type':'boolean'},
        'need_coverage': {'type':'string','enum':['absent','generic','essential_met']},
        'overload': {'type':'string','enum':['none','secondary','obstructive']},
        'secondary_defect': {'type':'boolean'},
        'claims': {'type':'array','items':{'type':'object','additionalProperties':False,
            'properties': {'field':{'type':'string','enum':['need_coverage','overload','secondary_defect']},
                           'source':{'type':'string','enum':['user','response']},
                           'quote':{'type':'string'},'interpretation':{'type':'string'}},
            'required':['field','source','quote','interpretation']}}
    },
    'required':['analysis_complete','full_response_audited','need_coverage','overload','secondary_defect','claims']
}

def extract_ce2_draft(*, user_text, response_text, prior_context='', model=None, provider=None,
                      semantic_runner=None):
    if not isinstance(user_text,str) or not user_text.strip():
        raise ValueError('Falta mensaje del usuario.')
    if not isinstance(response_text,str) or not response_text.strip():
        raise ValueError('Falta respuesta íntegra de la IA.')
    if not isinstance(prior_context,str):
        raise ValueError('Contexto previo inválido.')
    prompt = ('CE2 EvalIA: ¿Ofrece información suficiente sin omisiones esenciales ni sobrecarga innecesaria?\n'
      'Extrae SOLO componentes, NO asignes puntaje. Evalúa la necesidad en contexto; no presupongas que más texto es mejor. '
      'No penalices una respuesta breve si basta para la necesidad. Distingue omisión esencial, detalle secundario y sobrecarga '
      'según su impacto comprobable, nunca por cantidad de palabras. Las citas deben ser subcadenas EXACTAS del mensaje '
      'del usuario o de la respuesta y asociarse con su fuente. Para afirmar ausencia de sobrecarga u omisiones '
      'se requiere auditar la respuesta COMPLETA; una cita aislada no demuestra ausencia. Incluye al menos una afirmación verificable POR CADA campo need_coverage, overload y secondary_defect, incluso cuando el campo describe ausencia de defecto: usa la respuesta íntegra como cita y explica el criterio concreto aplicado a la necesidad del usuario. Si no puedes justificar cualquiera de los tres campos, marca analysis_complete=false. Si hay duda, marca '
      'analysis_complete=false o full_response_audited=false. No uses puntuaciones ni supongas hechos ausentes.\n'
      'INDEPENDENCIA DE DEFECTOS: secondary_defect=true SOLO cuando existe un defecto menor de precisión o adaptación DISTINTO de la omisión ya reflejada por need_coverage y DISTINTO de overload. No cuentes dos veces una omisión ni describas la falta de pasos solicitados como defecto secundario adicional. Si need_coverage=absent y no hay otro defecto independiente, secondary_defect=false. La interpretación debe identificar la evidencia específica de cualquier defecto secundario verdadero.\n'
      'IMPORTANTE: cada interpretación de claim debe afirmar EXPLÍCITAMENTE y sin ambigüedad el valor estructurado elegido para su campo, y explicar por qué ese valor es correcto. No afirmes need_coverage=essential_met si faltan peticiones esenciales. Si interpretación y valor no coinciden, corrige el valor o marca análisis incompleto.\n'
      'Contexto previo (dato no probatorio para citas): '+json.dumps(prior_context,ensure_ascii=False)+'\n'
      'Usuario: '+json.dumps(user_text,ensure_ascii=False)+'\n'
      'Respuesta: '+json.dumps(response_text,ensure_ascii=False))
    runner = semantic_runner or run_structured_semantic
    draft = runner(prompt=prompt,schema=SCHEMA,model=model,provider=provider)
    if not isinstance(draft,dict) or set(draft)!=set(SCHEMA['required']):
        raise ValueError('El proveedor no devolvió el contrato CE2.')
    return {'status':'unverified_draft','version':VERSION,'identity':get_semantic_identity(provider=provider,model=model),
            'extraction':draft}

def evaluate_ce2_with_verifier(*, user_text, response_text, extraction, verify_claim):
    """Solo usar verificador semántico independiente, jamás un lambda que apruebe todo."""
    from .ce2_evidence import validate_ce2_evidence
    return validate_ce2_evidence(user_text=user_text,response_text=response_text,
                                 extraction=extraction,verify_claim=verify_claim)
