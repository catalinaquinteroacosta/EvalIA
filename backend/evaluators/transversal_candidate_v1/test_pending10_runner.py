import asyncio,json
from copy import deepcopy
from .pending10_runner import IntegrationRunner,create_app
from .pending10_ratified import final_definitions,VERSION
from crisis_semantic.domain import load_contracts
from crisis_semantic.predicate_catalog import definitions

def test_http_selects_final_composition_for_all_104_and_preserves_unknowns():
    seen={};lookup=[]
    class Reader:
        qualified_components=set()
        def run(self,stage,system,content,schema,ids,identity):
            seen.update(deepcopy(content['predicates']))
            assert content['conversation']['current_turn']==1
            assert not content['conversation']['history']
            return dict(reviewed_entire_context=True,claims=[dict(id=k,state='unknown',citations=[],reason='Transport fixture; not a semantic observation.') for k in ids])
    def resolve(response_id):
        lookup.append(response_id)
        return dict(rubric_type='crisis',model='m',turn=1,conversation='c',originals=[
            dict(conversation='c',model='m',turn=1,user='Necesito apoyo.',response='Podemos conversar.'),
            dict(conversation='c',model='m',turn=2,user='Future input forbidden.',response='Future evidence forbidden.')])
    app=create_app(IntegrationRunner(resolve,crisis_provider=Reader()))
    messages=[]
    async def receive():return {'type':'http.request','body':b'','more_body':False}
    async def send(message):messages.append(message)
    coroutine=app(dict(type='http',method='POST',path='/api/responses/1/evaluate'),receive,send)
    try:coroutine.send(None)
    except StopIteration:pass
    else:raise AssertionError('Unexpected external await in in-process ASGI test')
    assert messages[0]['status']==200 and lookup==[1]
    payload=json.loads(messages[1]['body'])
    assert payload['release']==VERSION
    assert len(payload['indicator_results'])==104
    assert payload['aggregation']['global_v2'] is None
    assert payload['review_required']
    expected=final_definitions(definitions(load_contracts()[0],list(load_contracts()[0])))
    assert seen==expected
    assert all(r['score'] is None for r in payload['indicator_results'])

def test_unconfigured_provider_fails_without_fabricating_results():
    r=IntegrationRunner(lambda _:dict(rubric_type='crisis'))
    try:r.evaluate_response(1)
    except RuntimeError as e:assert str(e)=='crisis_provider_not_configured'
    else:assert False
