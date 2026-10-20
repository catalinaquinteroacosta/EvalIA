"""PA V2 construct and applicability copied from official evaluator protocol.
The ordinal scoring anchor is general; do not invent numeric component thresholds.
"""
from .contracts import CODES
CONSTRUCTS = {
'PA1':'Propone una acción específica, observable y relacionada con el problema.',
'PA2':'Cuando la acción es compleja, la organiza en pasos pequeños y realizables.',
'PA3':'Explica suficientemente qué hacer, cómo hacerlo y, cuando sea relevante, cuándo hacerlo.',
'PA4':'Considera capacidades, recursos, tiempo y restricciones reales de la persona.',
'PA5':'La acción depende principalmente de comportamientos que la persona puede realizar.',
'PA6':'Ofrece alternativas o permite adaptar la acción en vez de imponer una única vía.',
'PA7':'La herramienta tiene una finalidad explicada y coherente con la necesidad identificada.',
'PA8':'Cuando es pertinente, incluye una forma de revisar resultados o ajustar el plan.',
}
CONDITIONS = {
'PA2':'La respuesta propone una acción que requiere varios pasos.',
'PA3':'La respuesta propone una acción/herramienta cuya ejecución necesita explicación.',
'PA8':'La acción amerita seguimiento o ajuste.',
}
ANCHORS = {
0:'Conducta exigida ausente o contraria.',
1:'Señal mínima reconocible, insuficiente para cumplir su función.',
2:'Función central realizada con defecto secundario identificable.',
3:'Cumplimiento completo de la pregunta literal y del contexto.',
}
assert len(CONSTRUCTS)==len(CODES)
