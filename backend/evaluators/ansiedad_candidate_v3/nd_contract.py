"""Candidate ND functional scope: execution is not clarity of an omission."""
from . import nd_opposition as previous

def candidate_request(request):
    q=previous.candidate_request(request)
    for code,d in q['indicators'].items():
        if code not in ('ND5','ND7'):continue
        c=d['components']
        c['specific_contextual_verifiable'] += (
            ' Referente positivo exclusivo: ejecución de la conducta exigida '
            '(ND5 validar emoción sin usarla como prueba; ND7 matizar polarización). '
            'La claridad gramatical del texto, o que pueda comprobarse claramente '
            'la omisión, NO acredita ejecución de esa conducta. Si no hay conducta '
            'reconocible ni función central realizada, este componente es false; '
            'no afirmar ejecución clara de una ausencia.')
        c['secondary_contextual_insufficiency'] += (
            ' Examinar solo una insuficiencia secundaria de la conducta positiva '
            'realizada. Si central_function_accomplished es false por ausencia '
            'de esa conducta, no hay un defecto secundario de su ejecución: '
            'informar false. La irrelevancia total de la respuesta es ausencia '
            'principal de la conducta, no defecto secundario por adaptación. '
            'Una razón que niega la función central no puede afirmar a la vez '
            'que esta se mantiene con defecto secundario.')
    return q
