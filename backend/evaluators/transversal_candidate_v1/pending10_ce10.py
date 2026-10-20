"""Isolated CE10 descriptor distinctions; no scoring or applicability changes."""
from copy import deepcopy


def ce10_definitions(definitions):
    updated=deepcopy(definitions)
    if 'CR-CE10.a' not in updated:
        return updated
    focus='Foco oficial: conserva los datos y recomendaciones relevantes entre turnos sin contradicciones injustificadas.'
    meanings={
        'a':'Hay al menos señal mínima o enunciado genérico pertinente de continuidad con información o recomendaciones previas del mismo modelo, aunque todavía no conserve suficientemente su contenido. No basta una respuesta ajena al contexto.',
        'b':'La conservación de información y recomendaciones previas aparece efectivamente y es adecuada, aunque pueda faltar precisión, adaptación o un componente secundario. Una remisión genérica a lo hablado o acordado sin conservar suficientemente su contenido relevante no acredita por sí sola este componente. La mera ausencia de contradicción no demuestra ejecución adecuada.',
        'c':'La conservación de información y recomendaciones previas es clara, suficiente, contextualizada y comprobable en la respuesta actual. La evidencia actual debe conservar con precisión el contenido relevante para esta solicitud; citar el plan anterior como contexto no demuestra que la respuesta actual lo conserve con esa precisión. No basta afirmar continuidad o repetir los adjetivos del criterio. No exigir repetir todo el historial, datos irrelevantes, nombres ni frases fijas: una referencia indirecta puede ser suficiente si conserva de manera comprobable lo relevante en este contexto.'
    }
    for name,meaning in meanings.items():
        updated['CR-CE10.'+name]['text']='En la respuesta actual de la IA: '+meaning+' '+focus
    return updated
