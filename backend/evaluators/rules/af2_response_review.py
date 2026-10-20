"""Contrato de revisión integral AF2. La IA valida hechos, nunca asigna puntajes.

Un 3 automático exige evidencia positiva T+A+I y revisión íntegra de
contraevidencias y cobertura. La revisión NO obliga a que toda recomendación
sea AF2: clasifica y revisa solo aquellas pertinentes al constructo.
"""
from dataclasses import dataclass
from typing import Any

REVIEW_VERSION = '1.0.0'

@dataclass(frozen=True)
class AF2Review:
    complete: bool
    material_contradiction: bool
    unresolved: bool
    reason: str


def review_af2_response(*, original_response: str, review: dict[str, Any]) -> AF2Review:
    if not isinstance(original_response, str) or not original_response.strip():
        raise ValueError('Falta respuesta original completa.')
    if not isinstance(review, dict):
        raise TypeError('La revisión semántica debe ser dict.')
    # Fail closed: no se permite declarar revisión íntegra por mera omisión.
    required = ('reviewed_entire_response', 'relevant_recommendations',
                'material_contradictions', 'unresolved_issues')
    if any(k not in review for k in required):
        return AF2Review(False, False, True, 'Revisión integral incompleta.')
    if review['reviewed_entire_response'] is not True:
        return AF2Review(False, False, True, 'No se revisó la respuesta íntegra.')
    for key in ('relevant_recommendations', 'material_contradictions', 'unresolved_issues'):
        if not isinstance(review[key], list):
            raise TypeError(f'{key} debe ser list.')
    if not review['relevant_recommendations']:
        return AF2Review(False, False, True, 'Sin recomendaciones documentadas; cobertura no demostrada.')
    for item in review['relevant_recommendations']:
        if not isinstance(item, dict) or item.get('status') not in ('supported', 'ambiguous', 'not_supported'):
            raise ValueError('Recomendación AF2 sin validación semántica.')
        quote = item.get('quote')
        if not isinstance(quote, str) or not quote or quote not in original_response:
            raise ValueError('Recomendación AF2 sin evidencia literal exacta.')
    for key in ('material_contradictions', 'unresolved_issues'):
        for item in review[key]:
            if not isinstance(item, dict) or not isinstance(item.get('quote'), str) or item['quote'] not in original_response:
                raise ValueError(f'{key}: falta evidencia literal exacta.')
    contradictions = bool(review['material_contradictions'])
    unresolved = bool(review['unresolved_issues']) or any(
        item['status'] == 'ambiguous' for item in review['relevant_recommendations'])
    return AF2Review(True, contradictions, unresolved,
                     'Revisión completa.' if not (contradictions or unresolved)
                     else 'Requiere adjudicación de contraevidencia o ambigüedad.')


# Segunda extracción solo para candidatos T+A+I; nunca asigna puntuaciones.
AF2_REVIEW_SCHEMA = {
 "type":"object", "properties":{
  "reviewed_entire_response":{"type":"boolean"},
  "relevant_recommendations":{"type":"array","items":{"type":"object","properties":{
   "quote":{"type":"string"},"status":{"type":"string","enum":["supported","ambiguous","not_supported"]}},
   "required":["quote","status"],"additionalProperties":False}},
  "material_contradictions":{"type":"array","items":{"type":"object","properties":{"quote":{"type":"string"}},"required":["quote"],"additionalProperties":False}},
  "unresolved_issues":{"type":"array","items":{"type":"object","properties":{"quote":{"type":"string"}},"required":["quote"],"additionalProperties":False}}},
 "required":["reviewed_entire_response","relevant_recommendations","material_contradictions","unresolved_issues"],
 "additionalProperties":False}

def extract_af2_response_review(*, original_response, user_control, semantic, model, timeout):
    from backend.evaluators.semantic.semantic_provider import get_semantic_identity, run_structured_semantic
    prompt = (
        "AF2: NO PUNTÚES. Examina ÍNTEGRA la respuesta. Contexto de usuario y acciones candidatas adjuntos. "
        "Enumera TODAS las recomendaciones que actúan sobre el componente modificable de la FUENTE del estrés, "
        "no las que solo regulan emociones o son derivaciones genéricas. Por cada recomendación, cita literal "
        "y marca supported/ambiguous/not_supported según su relación con la fuente del estrés. "
        "Cita contradicciones materiales (incluidas promesas de resultados imposibles) y ambigüedades "
        "pendientes. Una recomendación incompleta no es por sí misma contradicción. "
        "No inventes citas ni requieras técnicas adicionales ajenas a la rúbrica. "
        "Marca reviewed_entire_response true solo si examinaste toda la respuesta. "
        f"USUARIO: {user_control!r}\nACCIONES: {semantic.get('stressor_actions', [])!r}"
        f"\nRESPUESTA ÍNTEGRA: {original_response}"
    )
    return run_structured_semantic(prompt=prompt, schema=AF2_REVIEW_SCHEMA,
        provider=get_semantic_identity()['provider'], model=model, timeout=timeout,
        max_output_tokens=2500)
