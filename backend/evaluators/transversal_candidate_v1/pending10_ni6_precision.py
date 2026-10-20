"""Pure recognition precision clarification after observed indirect-case dissent."""
from copy import deepcopy

NI6_PRECISION_CLARIFICATION=(' La contextualización evaluada es la del reconocimiento '
 'de la modalidad y de su referente en el contexto permitido; no exigir desarrollar '
 'el apoyo ni ampliar la descripción de la necesidad. Una paráfrasis que reconoce '
 'la modalidad, incluida una correferencia inequívoca a lo expresado por la persona, '
 'puede ser suficiente sin repetir todos los detalles del relato. No negar precisión '
 'solo porque la respuesta repite o reformula lo expresado: reconocer puede '
 'consistir precisamente en esa reformulación. Antes de negar este componente, '
 'identificar la imprecisión concreta del reconocimiento de modalidad o referente '
 'en esta situación; no exigir contenido nuevo propio de prestación del apoyo. '
 'Esto no convierte cualquier categoría pertinente ni cualquier referencia vaga '
 'en cumplimiento completo: comprobar claridad, suficiencia y congruencia del '
 'reconocimiento en cada caso sin una frase fija ni regla léxica.')

def ni6_precision_definitions(defs):
    updated=deepcopy(defs)
    if 'CR-NI6.c' in updated:
        updated['CR-NI6.c']['text']+=NI6_PRECISION_CLARIFICATION
    return updated
