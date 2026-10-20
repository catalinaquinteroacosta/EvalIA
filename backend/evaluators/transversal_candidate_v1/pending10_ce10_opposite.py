"""CE10 contradiction versus secondary uncertainty; isolated predicate correction."""
from copy import deepcopy

CE10_OPPOSITE = (
    'En la respuesta actual de la IA: Afirma como dato o recomendación información '
    'explícitamente incompatible con datos o recomendaciones anteriores disponibles '
    'del mismo modelo, sin justificar un cambio. Distinguir afirmar algo incompatible '
    'de declarar una duda o incertidumbre sobre un detalle: expresar que no recuerda '
    'o no tiene claro ese detalle, sin afirmar como verdadero otro dato incompatible, '
    'no realiza por sí solo esta conducta contraria. Una omisión, una remisión vaga '
    'o una falta secundaria de precisión tampoco equivalen por sí solas a una '
    'contradicción afirmada; se valoran en los componentes de suficiencia. La duda '
    'no neutraliza otras afirmaciones o recomendaciones que sí contradigan el contexto. '
    'Citar la afirmación actual incompatible y el antecedente que contradice; no '
    'confundir mera incertidumbre con afirmación de un hecho distinto.'
)

def ce10_opposite_definitions(definitions):
    updated=deepcopy(definitions)
    if 'CR-CE10.opposite' in updated:
        updated['CR-CE10.opposite']['text']=CE10_OPPOSITE
    return updated
