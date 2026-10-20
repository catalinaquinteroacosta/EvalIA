import pytest
from backend.evaluators.ansiedad_semantic.complete_json_recovery import recover

def payload(content):return {'choices':[{'finish_reason':'length','message':{'content':content}}]}
Q={'_response_schema':{'type':'object','properties':{'fact':{'type':'boolean'}},'required':['fact'],'additionalProperties':False}}

def test_closed_json_and_trailing_whitespace_preserve_fact():
    assert recover(Q,payload('{"fact":false} \t\n'))=={'fact':False}

@pytest.mark.parametrize('content',['{"fact":fal','{"fact":false} extra','{}','{"fact":false,"score":3}'])
def test_no_repairs_or_omissions_or_extra_fields(content):
    with pytest.raises((ValueError,KeyError)):recover(Q,payload(content))
