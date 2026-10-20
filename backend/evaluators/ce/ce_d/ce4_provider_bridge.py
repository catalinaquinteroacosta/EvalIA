"""Borrador semántico CE4; NUNCA se considera verificado ni asigna puntajes."""
import json
from backend.evaluators.semantic.semantic_provider import run_structured_semantic,get_semantic_identity
from .ce4_evidence import validate_ce4_evidence
VERSION='ce4-rubric-0.2.0'
SCHEMA = {'type': 'object', 'additionalProperties': False, 'properties': {'analysis_complete': {'type': 'boolean'}, 'full_response_audited': {'type': 'boolean'}, 'applicable': {'type': 'boolean'}, 'applicability_evidence': {'type': 'object', 'additionalProperties': False, 'properties': {'source': {'type': 'string', 'enum': ['response']}, 'quote': {'type': 'string'}, 'interpretation': {'type': 'string'}}, 'required': ['source', 'quote', 'interpretation']}, 'claims': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False, 'properties': {'source': {'type': 'string', 'enum': ['user', 'response']}, 'quote': {'type': 'string'}, 'interpretation': {'type': 'string'}}, 'required': ['source', 'quote', 'interpretation']}}, 'rubric_execution': {'type': 'string', 'enum': ['omitted_or_opposite', 'minimal_generic', 'adequate_limited', 'clear_contextual_verifiable']}}, 'required': ['analysis_complete', 'full_response_audited', 'applicable', 'applicability_evidence', 'claims', 'rubric_execution']}
def extract_ce4_draft(*,user_text,response_text,prior_context='',model=None,provider=None,semantic_runner=None):
    if not isinstance(user_text,str) or not user_text.strip(): raise ValueError('Falta usuario')
    if not isinstance(response_text,str) or not response_text.strip(): raise ValueError('Falta respuesta íntegra')
    if not isinstance(prior_context,str): raise ValueError('Contexto inválido')
    prompt = (
        "CE4: Cuando la extensión lo requiere, "
        "¿emplea párrafos o enumeraciones funcionales? "
        "Extrae evidencia semántica sin asignar puntos. "
        "Primero determina si la extensión de la respuesta "
        "hace necesaria estructura visual, independientemente "
        "de si ya existen párrafos o enumeraciones. "
        "No uses umbrales fijos de palabras ni actives CE4 "
        "solo porque el usuario solicite pasos. "
        "Si no aplica, usa claims=[] y rubric_execution="
        "'omitted_or_opposite' como valor técnico ignorado. "
        "Si aplica, extrae la categoría rubric_execution: "
        "omitted_or_opposite (omisión o conducta contraria); "
        "minimal_generic (señal mínima o genérica insuficiente); "
        "adequate_limited (conducta adecuada con precisión "
        "o adaptación limitada); "
        "clear_contextual_verifiable (conducta clara, "
        "específica, contextualizada y comprobable). "
        "No asignes puntuaciones. "
        "Incluye evidencia literal exacta de la respuesta "
        "para aplicabilidad y hasta tres claims pertinentes. "
        "Ante incertidumbre marca analysis_complete=false. "
        "Evalúa la respuesta completa. "
        + "\nContexto: " + json.dumps(prior_context, ensure_ascii=False)
        + "\nUsuario: " + json.dumps(user_text, ensure_ascii=False)
        + "\nRespuesta: " + json.dumps(response_text, ensure_ascii=False)
    )
    result=(semantic_runner or run_structured_semantic)(prompt=prompt,schema=SCHEMA,model=model,provider=provider)
    if not isinstance(result,dict) or set(result)!=set(SCHEMA['required']): raise ValueError('Borrador incompleto')
    return {'status':'unverified_draft','version':VERSION,'identity':get_semantic_identity(provider=provider,model=model),'extraction':result}
def evaluate_ce4_with_verifier(*,user_text,response_text,extraction,verify_claim,reconcile_claim=None):
    return validate_ce4_evidence(
        user_text=user_text,
        response_text=response_text,
        extraction=extraction,
        verify_claim=verify_claim,
        reconcile_claim=reconcile_claim,
    )
