"""Synthetic offline provenance guard fixtures; never model qualification."""
import json
from hashlib import sha256
from copy import deepcopy
import pytest
from backend.luna_application import request_key
from backend.luna_reader import usage_cost
from backend.luna_qualification import verify_sync_binding

def bundle(tmp_path):
    body={'model':'gpt-6-luna','max_output_tokens':100}
    key,wire=request_key(body,'responses')
    manifest={'requests':[{'endpoint':'responses','body':body}]}
    def put(name,value):
        path=tmp_path/name;path.write_text(json.dumps(value),encoding='utf8')
        return {'path':str(path),'sha256':sha256(path.read_bytes()).hexdigest()}
    m=put('manifest.json',manifest)
    auth=dict(explicit_user_approval=True,model='gpt-6-luna',mode='sync',scope='offline fixture',
        max_usd='1',max_requests=1,allow_definitive_950=False,
        sealed_manifest_sha256=m['sha256'],manifest_path=m['path'],private_directory=str(tmp_path))
    raw=dict(id='controlled-offline-response',model='gpt-6-luna',usage=dict(input_tokens=10,output_tokens=5))
    response=put(key+'.response.json',raw)
    receipt=dict(request_sha256=key,response_sha256=response['sha256'],mode='sync',
        http_status=200,remote_request_id='controlled-offline-request',endpoint='responses',
        model='gpt-6-luna',response_id=raw['id'],actual_usd=str(usage_cost(raw,'sync')))
    records=dict(manifest=m,authorization=put('authorization.json',auth),
        intent=put(key+'.intent.json',dict(request_sha256=key,endpoint='responses',reserved_usd='1')),
        receipt=put(key+'.receipt.json',receipt),request=put(key+'.request.json',json.loads(wire)),response=response)
    return {},dict(url='/v1/responses',method='POST',body=body),raw,dict(sync_evidence=records)

def test_exact_sync_chain_accepted_offline(tmp_path):
    assert verify_sync_binding(*bundle(tmp_path))

@pytest.mark.parametrize('field,value',[
    ('http_status',500),('remote_request_id',''),('endpoint','chat/completions'),
    ('model','other'),('response_id','crossed'),('actual_usd','1')])
def test_even_rehashed_receipt_cannot_cross_binding(tmp_path,field,value):
    from pathlib import Path
    args=bundle(tmp_path);records=args[3]['sync_evidence'];path=Path(records['receipt']['path'])
    receipt=json.loads(path.read_text());receipt[field]=value;path.write_text(json.dumps(receipt))
    records['receipt']['sha256']=sha256(path.read_bytes()).hexdigest()
    assert not verify_sync_binding(*args)

def test_sync_chain_cannot_authorize_definitive_cases(tmp_path):
    from pathlib import Path
    args=bundle(tmp_path);record=args[3]['sync_evidence']['authorization'];path=Path(record['path'])
    auth=json.loads(path.read_text());auth['allow_definitive_950']=True;path.write_text(json.dumps(auth))
    record['sha256']=sha256(path.read_bytes()).hexdigest()
    assert not verify_sync_binding(*args)
