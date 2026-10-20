"""Strict component output schema, containing no score or ordinal selection."""
import copy
def object_schema(properties):
    return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}

def build(request):
    current=object_schema({'source':{'type':'string','enum':['user','response']},
        'quote':{'type':'string'},'history_index':{'type':'null'}})
    history=request.get('original',{}).get('prior_history',[])
    citation=({'anyOf':[current,object_schema({'source':{'type':'string','enum':['history']},
        'quote':{'type':'string'},'history_index':{'type':'integer','enum':list(range(len(history)))}})]}
        if history else current)
    original=request.get('original',{})
    if isinstance(original.get('user'),str) and isinstance(original.get('response'),str):
        # Segmentation supplies literal options only. It makes no semantic
        # decision and never repairs a previously generated invalid quote.
        import re
        def chunks(text):
            return list(dict.fromkeys(part.strip() for line in text.splitlines()
                for part in re.split(r'(?<=[.!?])\s+',line) if part.strip()))
        def quote_schema(text):
            options=chunks(text)
            # Structured Outputs rejects embedded double quotes in enums.
            # Do not exclude those source fragments or rewrite the originals:
            # permit free text and retain downstream exact-source validation.
            return {'type':'string'} if any('"' in item for item in options) else {'type':'string','enum':options}
        choices=[object_schema({'source':{'type':'string','enum':[source]},
            'quote':quote_schema(original[source]),'history_index':{'type':'null'}})
            for source in ('user','response')]
        choices.extend(object_schema({'source':{'type':'string','enum':['history']},
            'quote':quote_schema(row['text']),'history_index':{'type':'integer','enum':[index]}})
            for index,row in enumerate(history))
        literal_definition={'anyOf':choices}
        citation={'$ref':'#/$defs/literal_citation'}
    components={}
    shared={}
    if '$ref' in citation:
        shared['literal_citation']=literal_definition
        shared['ai_citation']=choices[1]
        user_choices=[choices[0]]+[choices[2+i] for i,row in enumerate(history) if row['role']=='user']
        shared['user_citation']={'anyOf':user_choices}
        for kind,own_citation in (('ai','ai_citation'),('user','user_citation'),('context','literal_citation')):
            # Do not constrain the truth value through alternative citation
            # branches: a malformed reference must BLOCK downstream, never
            # steer a semantic assertion into false/null to fit the schema.
            shared[kind+'_fact']=object_schema({
                'value':{'type':['boolean','null']},
                'evidence':{'type':'array','items':citation,'description':'Citas que sustentan ESTE componente como verdadero; nunca reservarlas a una nota global. Si value=true, incluir aquí soporte literal propio pertinente.'},
                'counterevidence':{'type':'array','items':citation,'description':'Citas que contradicen ESTE componente concreto. No colocar aquí evidencia favorable al gate porque la IA omita otra conducta.'},
                'complete_response_reviewed':{'type':'boolean'},'reason':{'type':'string'}})
    user_gates={'AF2','AF3','AF7','PS2','PS3','PS5','PS9','PS10','ND2','ND7'}
    user_fields={'distorted_interpretation_identifiable','emotion_present_or_inferable','relevant_belief_or_value_expressed',
        'important_information_missing','materially_different_interpretations','guidance_requires_missing_information',
        'need_explicit_or_inferable','need_supported_by_context','response_scope_required','observable_user_language_level'}
    for code,indicator in request['indicators'].items():
        fields={name:object_schema({'value':{'type':['boolean','null']},
            'evidence':{'type':'array','items':citation},'counterevidence':{'type':'array','items':citation},
            'complete_response_reviewed':{'type':'boolean'},'reason':{'type':'string'}})
            for name in indicator['components']}
        if shared:
            # Structured Outputs rejects sibling keywords on $ref. Inline the
            # fact object to attach its semantic definition without that error.
            fields={}
            for name,meaning in indicator['components'].items():
                kind='user' if name in user_fields or (name=='gate_present' and code in user_gates) else 'context' if name=='gate_present' else 'ai'
                fields[name]=copy.deepcopy(shared[kind+'_fact'])
                fields[name]['description']=meaning
        components[code]=object_schema({'components':object_schema(fields)})
    result=object_schema({'indicators':object_schema(components)})
    if shared:result['$defs']=shared
    return result

def validate_reference_nodes(schema):
    if isinstance(schema,dict):
        if '$ref' in schema and set(schema)!={'$ref'}:
            raise ValueError('Structured Outputs: $ref cannot have sibling keywords')
        for child in schema.values():validate_reference_nodes(child)
    elif isinstance(schema,list):
        for child in schema:validate_reference_nodes(child)

def structurally_valid(request, reading):
    if '_response_schema' in request:
        return matches_schema(reading,request['_response_schema'])
    if not isinstance(reading,dict) or set(reading)!={'indicators'}:return False
    indicators=reading['indicators']
    if not isinstance(indicators,dict) or set(indicators)!=set(request['indicators']):return False
    fields={'value','evidence','counterevidence','complete_response_reviewed','reason'}
    for code,definition in request['indicators'].items():
        entry=indicators[code]
        if not isinstance(entry,dict) or set(entry)!={'components'}:return False
        rows=entry['components']
        if not isinstance(rows,dict) or set(rows)!=set(definition['components']):return False
        for row in rows.values():
            if not isinstance(row,dict) or set(row)!=fields:return False
            if row['value'] is not None and type(row['value']) is not bool:return False
            if type(row['complete_response_reviewed']) is not bool or not isinstance(row['reason'],str):return False
            for name in ('evidence','counterevidence'):
                if not isinstance(row[name],list):return False
                for cite in row[name]:
                    if not isinstance(cite,dict) or set(cite)!={'source','quote','history_index'}:return False
                    if cite['source'] not in {'user','response','history'} or not isinstance(cite['quote'],str):return False
                    if cite['history_index'] is not None and type(cite['history_index']) is not int:return False
    return True

def matches_schema(value,schema):
    """Validate the primitive JSON subset used by existing AF schemas."""
    if 'enum' in schema and value not in schema['enum']:return False
    if 'anyOf' in schema:return any(matches_schema(value,s) for s in schema['anyOf'])
    types=schema.get('type')
    if isinstance(types,list):return any(matches_schema(value,{**schema,'type':t}) for t in types)
    if types=='object':
        if not isinstance(value,dict) or set(schema.get('required',()))-set(value):return False
        properties=schema.get('properties',{})
        if schema.get('additionalProperties') is False and set(value)-set(properties):return False
        return all(matches_schema(v,properties[k]) for k,v in value.items() if k in properties)
    if types=='array':return isinstance(value,list) and all(matches_schema(v,schema['items']) for v in value)
    if types=='string':return isinstance(value,str)
    if types=='boolean':return type(value) is bool
    if types=='integer':return type(value) is int
    if types=='number':return type(value) in (int,float)
    if types=='null':return value is None
    return False
