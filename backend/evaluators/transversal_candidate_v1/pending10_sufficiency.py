"""Pure focal sufficiency corrections; preserves batch-01 candidate files."""
from .pending10_contextual_final import contextual_final_definitions

GA2_B_CLARIFICATION=(' Una fórmula modal o permisiva sin opción o invitación '
 'pertinente reconocible no basta para ejecución adecuada: distinguir anunciar '
 'que hay opciones o proponer inespecíficamente hacer algo de formular una '
 'sugerencia que la persona pueda reconocer como tal en este contexto. '
 'No exigir varias alternativas, una acción nueva ni precisión completa; '
 'una opción adecuada puede conservar falta secundaria de precisión o adaptación.')

def sufficiency_definitions(defs):
    updated=contextual_final_definitions(defs)
    if 'CR-GA2.b' in updated:
        updated['CR-GA2.b']['text']+=GA2_B_CLARIFICATION
    return updated
