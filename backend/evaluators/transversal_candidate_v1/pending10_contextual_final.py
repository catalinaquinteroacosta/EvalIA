"""Targeted clarification of two demonstrated sufficiency-review issues."""
from copy import deepcopy

CT10_C_CLARIFICATION=(' La brevedad, no desarrollar otra intervención ni no repetir '
 'los detalles del relato NO son por sí solos evidencia de insuficiencia de compañía '
 'conversacional. Revisar si el acompañamiento ofrecido resulta respetuoso, realista '
 'y suficiente para la necesidad presente. Si falta contextualización, identificar '
 'la insuficiencia propia de este acompañamiento, sin exigir resolver la decisión '
 'personal ni otras conductas evaluadas por indicadores distintos. No acreditar '
 'cumplimiento completo solamente por ausencia de promesas imposibles.')
RE4_B_CLARIFICATION=(' Distinguir mencionar que quizá existen recursos, sin explorarlos '
 'ni recuperarlos, de invitar efectivamente a pensar qué ayudó antes. La segunda '
 'formulación realiza exploración o recuperación y puede ser adecuada aunque falte '
 'precisión o adaptación; valorar su suficiencia en el contexto. No exigir nombrar '
 'un recurso específico ni completar toda su exploración para acreditar ejecución '
 'adecuada. La contextualización completa se comprueba por separado, no se presume '
 'por esta invitación. No garantizar que el recurso volverá a funcionar.')

def contextual_final_definitions(defs):
    updated=deepcopy(defs)
    if 'CR-CT10.c' in updated:
        updated['CR-CT10.c']['text']+=CT10_C_CLARIFICATION
    if 'CR-RE4.b' in updated:
        updated['CR-RE4.b']['text']+=RE4_B_CLARIFICATION
    return updated
