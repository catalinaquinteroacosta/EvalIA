import copy
import pytest
from backend.evaluators.ansiedad_semantic.ce3_relation_grounding import request_with_relation_audit,validate_relation_reading
from backend.evaluators.ansiedad_semantic.closure_integral_live import source,prepare
from backend.evaluators.ansiedad_semantic.reader_schema import validate_reference_nodes,structurally_valid

def fixture():
    o={'response':'Llueve. Por eso llevo paraguas.'}
    r={'relation_audit':{'first_response_idea':'Llueve.','second_response_idea':'Por eso llevo paraguas.',
       'functional_relation_supported':True,'relation_explanation':'La lluvia explica llevar paraguas.',
       'anaphoric_reference_target':'response_idea','relation_depends_only_on_shared_user_topic':False,
       'mere_succession_is_only_ground':False,'complete_response_reviewed':True},
       'indicators':{'CE3':{'components':{'comprehensible_transitions':{'value':True}}}}}
    return o,r

def test_supported_connection_is_admissible():
    assert validate_relation_reading(*fixture())

@pytest.mark.parametrize('field',['relation_depends_only_on_shared_user_topic','mere_succession_is_only_ground'])
def test_generic_context_or_order_cannot_certify_relation(field):
    o,r=fixture();r['relation_audit'][field]=True
    with pytest.raises(ValueError):validate_relation_reading(o,r)

def test_user_endpoint_and_inconsistent_support_block():
    o,r=fixture();r['relation_audit']['first_response_idea']='Texto exclusivo del usuario'
    with pytest.raises(ValueError):validate_relation_reading(o,r)
    o,r=fixture();r['relation_audit']['functional_relation_supported']=False
    with pytest.raises(ValueError):validate_relation_reading(o,r)

def test_absence_is_not_manually_converted_to_a_grade():
    o,r=fixture();r['relation_audit']['functional_relation_supported']=False
    r['indicators']['CE3']['components']['comprehensible_transitions']['value']=False
    assert validate_relation_reading(o,r) is True
    assert 'score' not in r

def test_request_contains_no_target_grade_and_schema_references_valid():
    case,_=source('CE3-grounded');q=request_with_relation_audit(prepare(case)[0])
    validate_reference_nodes(q['_response_schema'])
    assert 'relation_audit' in q['_response_schema']['required']
    assert 'score' not in q['_response_schema']['properties']
    assert '$defs' not in q['_response_schema']
    # Custom schema must validate locally, not merely be accepted remotely.
    def materialize(s):
        if s.get('type')=='object':return {k:materialize(v) for k,v in s['properties'].items()}
        if s.get('type')=='array':return []
        if 'anyOf' in s:return materialize(s['anyOf'][0])
        if 'enum' in s:return s['enum'][0]
        t=s.get('type');t=t[0] if isinstance(t,list) else t
        return {'boolean':False,'null':None,'string':'test','integer':0}[t]
    assert structurally_valid(q,materialize(q['_response_schema']))
