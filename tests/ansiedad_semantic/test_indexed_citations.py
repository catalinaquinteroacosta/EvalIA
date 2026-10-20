import copy
import pytest
from backend.evaluators.ansiedad_semantic.indexed_citations import catalog, resolve_indices
from backend.evaluators.ansiedad_semantic.budgeted_reader import envelope


def request():
    return {'stage':'extract','original':{'user':'Relato.',
        'response':'Dice "no". Segunda frase.',
        'prior_history':[{'role':'user','text':'Anterior propio.'}]},
        'indicators':{'CE1':{'components':{'fact':'Conducta verificable'}}}}


def test_quotes_resolve_exactly_without_repairing_source():
    q=request();before=copy.deepcopy(q);rows=catalog(q)
    row=next(r for r in rows if r['quote']=='Dice "no".')
    raw={'evidence':[{k:row[k] for k in ('source','quote_index','history_index')}]}
    normalized=resolve_indices(raw,rows)
    assert normalized['evidence']==[{'source':'response','quote':'Dice "no".','history_index':None}]
    assert 'quote_index' in raw['evidence'][0]
    assert q==before


def test_cross_source_and_invalid_index_are_rejected():
    rows=catalog(request())
    for item in ({'source':'response','history_index':None,'quote_index':0},
                 {'source':'user','history_index':None,'quote_index':999},
                 {'source':'user','history_index':None,'quote_index':True}):
        with pytest.raises(ValueError):resolve_indices({'evidence':[item]},rows)


def test_paid_envelope_uses_indices_and_no_embedded_quote_enum():
    body=envelope(request(),'gpt-4.1-2025-04-14')
    schema=body['response_format']['json_schema']['schema']
    props=schema['$defs']['ai_citation']['properties']
    assert set(props)=={'source','quote_index','history_index'}
    assert props['quote_index']['enum']==[1,2]
    assert 'literal_citation_catalog' in body['messages'][1]['content']
