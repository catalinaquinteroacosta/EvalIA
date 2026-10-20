"""Candidate-only distinction between verified omission and contrary conduct."""
from copy import deepcopy

def candidate_request(request):
    q=deepcopy(request)
    for code,d in q['indicators'].items():
        if code not in ('ND5','ND7'):continue
        d['components']['opposite_behavior_present'] += (
            ' Distinguir ausencia verificada de conducta y realización de su contraria. '
            'Una respuesta irrelevante o que omite completamente la conducta no '
            'demuestra por sí sola conducta contraria. Para afirmar este componente '
            'identificar un mecanismo contrario observable: en ND5, invalidación '
            'emocional o uso de la emoción como prueba factual; en ND7, refuerzo '
            'observable de la polarización frente al matiz requerido. Si solo se '
            'verifica omisión y no hay ese mecanismo, informar false; si existe '
            'incertidumbre real, null. Mantener esta distinción independiente de '
            'required_behavior_recognizable y central_function_accomplished.')
    return q
