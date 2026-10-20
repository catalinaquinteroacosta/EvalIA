"""Independent claim audit; extracted proposals are not evidence or scores.

Unlike historical blind dual readings, this verifier receives the proposed
atomic claims to confirm/reject against originals. Python still requires
agreement; a rejected proposal remains BLOCKED, never silently replaced.
"""
import copy

def verification_request(request,extraction):
    if request['stage']!='independent_verify':raise ValueError('Only verification stage')
    result=copy.deepcopy(request)
    result['untrusted_proposed_components']=copy.deepcopy(extraction)
    result['independent_claim_audit_instruction']=(
        'Audita cada afirmación propuesta frente a los ORIGINALES completos y la definición '
        'específica de su componente. Las propuestas no son evidencia ni autoridad. Devuelve '
        'tu propio true/false/null con citas originales propias y razones independientes; '
        'no copies conclusiones por concordancia. No recibes ni seleccionas notas. '
        'Rechaza especialmente: confundir cualquier conducta con intento positivo, afirmar '
        'ejecución específica de una frase genérica, valorar claridad del texto en vez de '
        'la ejecución del constructo, completar una conjunción con solo una parte, '
        'atribuir conducta del usuario a la IA o penalizar otro indicador. '
        'Una frase puede ser gramaticalmente clara y no realizar específicamente la conducta. '
        'Contrasta value con reason y con lo que realmente demuestra la cita, incluyendo '
        'contraevidencia. Si discrepas, informa tu propio valor; Python conservará la discrepancia.')
    return result

class ClaimAuditReader:
    def __init__(self,reader):self.reader=reader;self.proposals={}
    def __call__(self,request):
        key=(request['original']['input_sha256'],tuple(request['indicators']))
        if request['stage']=='extract':
            output=self.reader(request);self.proposals[key]=copy.deepcopy(output);return output
        if key not in self.proposals:raise ValueError('No extraction proposal for these exact originals/codes')
        return self.reader(verification_request(request,self.proposals[key]))
