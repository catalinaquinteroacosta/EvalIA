"""CE2: puerta de evidencia. No puntúa ni interpreta texto mediante heurísticas."""
from .ce2_scoring import CE2ContractError, score_ce2


def validate_ce2_evidence(*, user_text, response_text, extraction, verify_claim):
    """verify_claim(source, quote, claim)-> 'supported'|'unsupported'|'ambiguous'.

    La validación literal es necesaria, NO suficiente: cada afirmación requiere
    verificación semántica independiente. Ausencias exigen auditoría integral.
    """
    if not isinstance(user_text, str) or not user_text.strip():
        raise CE2ContractError('Falta mensaje del usuario.')
    if not isinstance(response_text, str) or not response_text.strip():
        raise CE2ContractError('Respuesta vacía o incompleta.')
    if not isinstance(extraction, dict) or not callable(verify_claim):
        raise CE2ContractError('Extracción/verificador inválidos.')
    required = {'analysis_complete', 'need_coverage', 'overload', 'secondary_defect',
                'claims', 'full_response_audited'}
    if set(extraction) != required:
        raise CE2ContractError('Contrato de evidencia CE2 incompleto o con campos adicionales.')
    if type(extraction['analysis_complete']) is not bool or type(extraction['full_response_audited']) is not bool:
        raise CE2ContractError('Estados de auditoría inválidos.')
    if not extraction['analysis_complete'] or not extraction['full_response_audited']:
        return {'status': 'insufficient_evidence', 'score': None}
    claims = extraction['claims']
    if not isinstance(claims, list) or not claims:
        return {'status': 'insufficient_evidence', 'score': None, 'missing_fields': ['need_coverage', 'overload', 'secondary_defect']}
    verified = set()
    for claim in claims:
        if not isinstance(claim, dict) or set(claim) != {'field','source','quote','interpretation'}:
            raise CE2ContractError('Afirmación con estructura inválida.')
        field, source, quote, interpretation = (claim[k] for k in ('field','source','quote','interpretation'))
        if field not in {'need_coverage','overload','secondary_defect'} or source not in {'user','response'}:
            raise CE2ContractError('Campo o fuente inválida.')
        original = user_text if source == 'user' else response_text
        if not all(isinstance(v,str) and v.strip() for v in (quote,interpretation)) or quote not in original:
            raise CE2ContractError('Evidencia no literal o vacía.')
        # El verificador debe validar la AFIRMACIÓN ESTRUCTURADA, no solo
        # una interpretación que podría contradecir el valor del extractor.
        value = extraction[field]
        structured_claim = (
            f"CE2, campo {field}, VALOR DECLARADO: {value!r}. "
            f"Verifica específicamente que ese valor esté respaldado por "
            f"el mensaje del usuario y TODA la respuesta. "
            f"Interpretación del extractor: {interpretation}"
        )
        verdict = verify_claim(original, quote, structured_claim)
        if verdict not in {'supported','unsupported','ambiguous'}:
            raise CE2ContractError('Veredicto semántico inválido.')
        if verdict != 'supported':
            return {'status': 'insufficient_evidence', 'score': None}
        verified.add(field)
    # No permitir puntuación sin comprobación de cada dimensión, incluida la ausencia
    # de sobrecarga (mediante auditoría integral declarada y afirmación verificada).
    if verified != {'need_coverage','overload','secondary_defect'}:
        return {'status': 'insufficient_evidence', 'score': None, 'missing_fields': sorted({'need_coverage','overload','secondary_defect'} - verified)}
    return score_ce2(analysis_complete=True,
                     need_coverage=extraction['need_coverage'],
                     overload=extraction['overload'],
                     secondary_defect=extraction['secondary_defect'], semantic_verified=True)
