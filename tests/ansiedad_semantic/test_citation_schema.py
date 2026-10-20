from backend.evaluators.ansiedad_semantic.reader_schema import build,matches_schema

def citation_schema(history):
    schema=build({'original':{'prior_history':history},'indicators':{'EM6':{'components':{'x':'fact'}}}})
    return schema['properties']['indicators']['properties']['EM6']['properties']['components']['properties']['x']['properties']['evidence']['items']

def test_current_source_never_accepts_a_history_index():
    schema=citation_schema([])
    assert matches_schema({'source':'response','quote':'literal','history_index':None},schema)
    assert not matches_schema({'source':'response','quote':'literal','history_index':1},schema)
    assert not matches_schema({'source':'history','quote':'literal','history_index':0},schema)

def test_history_indices_bound_to_authorized_prior_context():
    schema=citation_schema([{'role':'user','text':'prior'}])
    assert matches_schema({'source':'history','quote':'prior','history_index':0},schema)
    assert not matches_schema({'source':'history','quote':'prior','history_index':1},schema)
    assert not matches_schema({'source':'history','quote':'prior','history_index':None},schema)
    assert not matches_schema({'source':'user','quote':'current','history_index':0},schema)

def test_literal_options_are_exact_original_substrings_not_repaired_outputs():
    original={'user':'Estoy triste. No sé qué hacer.', 'response':'Es comprensible.\nPuedes pedir apoyo.', 'prior_history':[]}
    schema=build({'original':original,'indicators':{'EM6':{'components':{'x':'fact'}}}})
    citation=schema['$defs']['literal_citation']
    for choice in citation['anyOf']:
        source=choice['properties']['source']['enum'][0]
        assert all(quote in original[source] for quote in choice['properties']['quote']['enum'])
    assert matches_schema({'source':'response','quote':'Es comprensible.','history_index':None},citation)
    assert not matches_schema({'source':'response','quote':'Es comprensible... Puedes pedir apoyo.','history_index':None},citation)
    assert not matches_schema({'source':'user','quote':'Es comprensible.','history_index':None},citation)
