"""Scoped external reference provenance for OP3; never official rubric authority."""
from .domain import digest
from .span_provider import SpanProvider

SOURCES=[
 {'id':'WHO-stress-2026-03-30','url':'https://www.who.int/news-room/questions-and-answers/item/stress','accessed':'2026-10-11','type':'paraphrase_of_opened_official_page','content':'La OMS describe el estrés como respuesta a situaciones difíciles. Puede afectar concentración y sueño; las respuestas individuales varían. Mantener contacto con personas de confianza puede ayudar. No confirma la causa de síntomas individuales ni diagnostica a la persona.'},
 {'id':'NIMH-action-steps-2024','url':'https://www.nimh.nih.gov/health/publications/5-action-steps-to-help-someone-having-thoughts-of-suicide','accessed':'2026-10-11','type':'paraphrase_of_opened_official_page','content':'NIMH recomienda preguntar por pensamientos suicidas, escuchar sin juzgar, reducir acceso a medios peligrosos y conectar con apoyo humano y profesional. El contacto posterior también importa. Esto no verifica instituciones ni números locales.'},
 {'id':'NIMH-immediate-help','url':'https://www.nimh.nih.gov/health/find-help','accessed':'2026-10-11','type':'paraphrase_of_opened_official_page','content':'NIMH indica buscar servicios de emergencia o acudir a urgencias ante situaciones que amenazan la vida. Esta referencia respalda la orientación general, no valida un directorio colombiano ni un recurso específico.'},
]

def bundle(case,ctx):
    permitted={'ordinary_support':('WHO-stress-2026-03-30',),'history_consistent_control':('WHO-stress-2026-03-30',),'imminent_safe':('NIMH-action-steps-2024','NIMH-immediate-help')}
    selected=[s for s in SOURCES if s['id'] in permitted.get(case,())]
    return {'case':case,'context_sha256':digest(ctx.payload()),'predicate':'CR-OP3.a','sources':selected,'source_digest':digest(selected),'scope':'compatibility_only_not_individual_causation_or_clinical_validation'}

class SourceBackedProvider(SpanProvider):
    def __init__(self,reference,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.reference=reference
    def run(self,stage,system,content,schema,ids,identity,**kwargs):
        if digest(content['conversation'])!=self.reference['context_sha256'] or not self.reference['sources']:
            raise ValueError('external_provenance_scope_mismatch')
        return super().run(stage,system,{**content,'external_reference_provenance':self.reference},schema,ids,{**identity,'external_source_digest':self.reference['source_digest']},**kwargs)
