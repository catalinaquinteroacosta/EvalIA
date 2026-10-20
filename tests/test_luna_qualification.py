"""Adversarial offline checks of the recorded qualification receipt chain."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import pytest
from backend.luna_qualification import verify_batch_binding, expected_body, read_artifact,validate_complete_wire

ROOT=Path(__file__).resolve().parent.parent
BASE=ROOT/'docs/economic_readers_step3_20261015'

def record(path):
    return dict(path=str(path),sha256=sha256(path.read_bytes()).hexdigest())

def bundle():
    src=BASE/'validation_v2';out=BASE/'execution_v2'
    paths=dict(manifest=src/'FROZEN_MANIFEST.json',requests=src/'REQUESTS_NOT_SENT.json',
        input=src/'LUNA_responses_NOT_SENT.jsonl',output=out/'output_file_id_0.jsonl',
        job=out/'JOB_0.json',state=out/'STATE.json')
    proof=dict(authorization=record(out/'AUTHORIZATION.json'),batch_evidence={k:record(v) for k,v in paths.items()})
    proof['execution_adapter']=record(BASE/'corrections_01/backup/luna_reader_replay_v2.py')
    request=json.loads(paths['input'].read_text(encoding='utf-8').splitlines()[0])
    outputs=[json.loads(s) for s in paths['output'].read_text(encoding='utf-8').splitlines()]
    response=next(x for x in outputs if x['custom_id']==request['custom_id'])
    reading=dict(batch_id=json.loads(paths['job'].read_text(encoding='utf-8'))['id'],
        custom_id=request['custom_id'],request_id=response['response']['request_id'])
    reading['execution_identity']=dict(model='gpt-6-luna',reader_source_sha256=proof['execution_adapter']['sha256'])
    return proof,request,response,reading

def test_original_recorded_batch_chain_is_consistent():
    assert verify_batch_binding(*bundle())

@pytest.mark.parametrize('target,field,value',[
    ('reading','batch_id','other_batch'),('reading','custom_id','other_case'),
    ('reading','request_id','other_request'),('response','custom_id','other_case'),
    ('request','url','/v1/chat/completions'),('request','method','GET'),
])
def test_cross_case_endpoint_or_receipt_rejected(target,field,value):
    proof,request,response,reading=deepcopy(bundle())
    {'request':request,'response':response,'reading':reading}[target][field]=value
    assert not verify_batch_binding(proof,request,response,reading)

def test_nonoriginal_response_and_cap_rejected():
    proof,request,response,reading=deepcopy(bundle())
    response['response']['body']['usage']['input_tokens']+=1
    assert not verify_batch_binding(proof,request,response,reading)
    proof,request,response,reading=deepcopy(bundle())
    request['body']['max_output_tokens']+=1
    assert not verify_batch_binding(proof,request,response,reading)

def test_artifact_mutation_rejected(tmp_path):
    path=tmp_path/'artifact.json';path.write_text('{}')
    rec=record(path);path.write_text('{"changed":true}')
    with pytest.raises(ValueError):read_artifact(rec)

@pytest.mark.parametrize('reviewed',[False,None,0,'true'])
def test_partial_or_nonboolean_context_review_rejected(reviewed):
    schema=dict(type='object',properties={'reviewed_entire_context':{'type':'boolean'}},required=['reviewed_entire_context'],additionalProperties=False)
    with pytest.raises(ValueError):validate_complete_wire({'reviewed_entire_context':reviewed},schema)

def test_complete_context_review_validated():
    validate_complete_wire({'reviewed_entire_context':True},{'type':'object'})

def test_regeneration_uses_actual_provider_schema_and_cap():
    from backend.luna_reader import LunaProvider,validate_schema
    from crisis_semantic.domain import Input,Turn
    from crisis_semantic.predicate_catalog import definitions
    from backend.evaluators.transversal_candidate_v1.adenda_ri2_v11 import final_definitions
    p=LunaProvider(lambda *args:None);code='CR-RI2'
    defs=final_definitions(definitions(p.contracts,[code]))
    ctx=Input(Turn(1,'Pienso hacerme daño.','¿Piensas hacerte daño?','fixture'),())
    extract=expected_body(p,code,'extract',ctx,defs)
    verify=expected_body(p,code,'verify',ctx,defs)
    assert extract['input'][0]!=verify['input'][0]
    assert extract['text']['format']['schema']==verify['text']['format']['schema']
    assert extract['reasoning']=={'effort':'none'} and extract['store'] is False
    assert extract['max_output_tokens']==1500
    assert json.loads(extract['input'][1]['content'])['conversation']==ctx.payload()

def test_ce10_own_compatibility_certificate_and_lineage():
    from backend.luna_reader import LunaProvider
    path=BASE/'corrections_02/CE10_OWN_CERTIFICATE_STEP31_OP5.json'
    if not path.exists():path=BASE/'corrections_02/CE10_OWN_CERTIFICATE_STEP31.json'
    if not path.exists():path=BASE/'corrections_02/CE10_OWN_CERTIFICATE_V3_FINAL_SCOPE.json'
    if not path.exists():path=BASE/'corrections_02/CE10_OWN_CERTIFICATE_V3_FINAL.json'
    if not path.exists():path=BASE/'corrections_02/CE10_OWN_CERTIFICATE_V3.json'
    if not path.exists():path=BASE/'corrections_01/CE10_OWN_CERTIFICATE_FINAL.json'
    proof=json.loads(path.read_text(encoding='utf-8'))['CR-CE10']
    p=LunaProvider(lambda *args:None,certificates={'CR-CE10':proof})
    # Historical identity remains rejected. Derivation is permitted only if
    # the verifier proves all effective bodies/contracts/receipts still exact.
    assert not p.qualified('CR-CE10')
    from backend.luna_reader import reader_identity
    proof=deepcopy(proof)
    identity=reader_identity('CR-CE10',p.contracts)
    proof['identity']=identity
    for case in proof['cases']:
        for reading in case['readings']:
            reading['validation_identity']=identity
    p.certificates={'CR-CE10':proof}
    assert p.qualified('CR-CE10')
    assert not p.qualified('CR-RI2')
    assert proof['cases'][0]['readings'][0]['execution_identity']['reader_source_sha256']!=proof['identity']['sources']['luna_reader.py']
    for field in ('batch_id','request_id','custom_id'):
        changed=deepcopy(proof);changed['cases'][0]['readings'][0][field]='crossed'
        p.certificates['CR-CE10']=changed
        assert not p.qualified('CR-CE10')
    changed=deepcopy(proof);changed['cases'][0]['readings'][0]['validation_identity']['reader_version']='old'
    p.certificates['CR-CE10']=changed
    assert not p.qualified('CR-CE10')
