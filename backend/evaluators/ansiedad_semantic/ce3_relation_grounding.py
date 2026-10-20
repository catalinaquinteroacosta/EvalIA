"""Factual relation audit for CE3; no desired grade or manual truth substitution."""
from copy import deepcopy
from .reader_schema import build,object_schema

def request_with_relation_audit(request):
    q=deepcopy(request)
    schema=build(q)
    # The existing primitive custom-schema validator does not resolve $ref.
    # Inline definitions here, without modifying the shared reader or its
    # historical output-validity records.
    definitions=schema.pop('$defs',{})
    def inline(value):
        if isinstance(value,dict):
            if '$ref' in value:return inline(deepcopy(definitions[value['$ref'].split('/')[-1]]))
            return {k:inline(v) for k,v in value.items()}
        if isinstance(value,list):return [inline(v) for v in value]
        return value
    schema=inline(schema)
    proof=object_schema({
        'first_response_idea':{'type':'string'},'second_response_idea':{'type':'string'},
        'functional_relation_supported':{'type':['boolean','null']},
        'relation_explanation':{'type':'string'},
        'anaphoric_reference_target':{'type':'string','enum':['response_idea','user_contribution','none','uncertain']},
        'relation_depends_only_on_shared_user_topic':{'type':['boolean','null']},
        'mere_succession_is_only_ground':{'type':['boolean','null']},
        'complete_response_reviewed':{'type':'boolean'}})
    schema['properties']['relation_audit']=proof
    schema['required'].append('relation_audit')
    q['_response_schema']=schema
    q['relation_audit_instruction']=(
        'Examina la conexión FUNCIONAL entre dos ideas de la respuesta actual. '
        'Copia ambas ideas literalmente, distintas del mensaje del usuario. '
        'Resuelve el referente de expresiones anafóricas contra quién habló. '
        'Una relación puede ser implícita si el contenido de las ideas la sustenta; '
        'no exigir conector ni fórmula fija. Explica la relación entre sus contenidos '
        '(secuencia, explicación, contraste u otra), no solo que ambas están en una '
        'conversación o que una contesta al usuario. Cambiar de tema o compartir el '
        'contexto del usuario no demuestra por sí solo una conexión funcional entre '
        'las ideas escritas. Distingue explicación de una idea previa de explicación '
        'de la actitud hacia el usuario. Si no hay relación sustentada, informa false; '
        'null solo por incertidumbre. Mantén los componentes y este análisis coherentes. '
        'No recibes ni seleccionas puntuaciones.')
    return q

def validate_relation_reading(original,reading):
    p=reading['relation_audit'];response=original['response']
    for name in ['first_response_idea','second_response_idea']:
        if not p[name].strip() or p[name] not in response:raise ValueError('CE3: relation endpoint not literal current AI idea')
    if p['first_response_idea']==p['second_response_idea']:raise ValueError('CE3: identical relation endpoints')
    if p['complete_response_reviewed'] is not True or not p['relation_explanation'].strip():raise ValueError('CE3: incomplete relational review')
    for name in ['functional_relation_supported','relation_depends_only_on_shared_user_topic','mere_succession_is_only_ground']:
        if type(p[name]) is not bool:raise ValueError('CE3: unresolved relational fact')
    transition=reading['indicators']['CE3']['components']['comprehensible_transitions']['value']
    if transition!=p['functional_relation_supported']:raise ValueError('CE3: transition contradicts relation audit')
    if transition and (p['relation_depends_only_on_shared_user_topic'] or p['mere_succession_is_only_ground']):
        raise ValueError('CE3: unsupported functional relation by own factual audit')
    return True
