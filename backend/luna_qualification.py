"""Own Luna qualification from exact recorded API pairs; never imports certificates."""
from pathlib import Path
from hashlib import sha256
import json
from math import isfinite

ROOT=Path(__file__).resolve().parent.parent

def read_artifact(record):
    """Require a content-addressed local evidence artifact; never fetch or infer."""
    path=Path(record['path'])
    if not path.is_file() or sha256(path.read_bytes()).hexdigest()!=record['sha256']:
        raise ValueError('qualification_artifact_integrity')
    return path,path.read_bytes()

def verify_batch_binding(proof, request, response, reading):
    """Link recorded authorization, sealed request and original Batch response.

    This verifies the preserved receipt chain, not a remote signature. A local
    fabricated bundle is not independent evidence of a remote API execution.
    """
    records=proof['batch_evidence'];loaded={}
    for name in ('manifest','requests','input','output','job','state'):
        path,data=read_artifact(records[name]);loaded[name]=(path,data)
    manifest=json.loads(loaded['manifest'][1]);requests=json.loads(loaded['requests'][1])
    sealed={str(Path(x['path']).resolve()):x['sha256'] for x in manifest}
    for name in ('requests','input'):
        path,data=loaded[name]
        if sealed.get(str(path.resolve()))!=sha256(data).hexdigest():return False
    authpath,authdata=read_artifact(proof['authorization']);auth=json.loads(authdata)
    if auth.get('explicit_user_approval') is not True or auth.get('model')!='gpt-6-luna' or auth.get('mode')!='Batch':return False
    budget=float(auth.get('max_usd',0));count=auth.get('max_requests',0)
    if not isfinite(budget) or budget<=0 or type(count) is not int or count<len(requests):return False
    # The human approval identifies this sealed directory, not an arbitrary JSON.
    if loaded['requests'][0].parent.name not in auth.get('scope',''):return False
    if len({x['custom_id'] for x in requests})!=len(requests):return False
    if request not in requests:return False
    execution_path,execution_bytes=read_artifact(proof['execution_adapter'])
    sealed_execution=next((x['sha256'] for x in manifest if Path(x['path']).as_posix()=='backend/luna_reader.py'),None)
    old_hash=sha256(execution_bytes).hexdigest()
    if old_hash!=sealed_execution:return False
    if reading.get('execution_identity')!={'model':'gpt-6-luna','reader_source_sha256':old_hash}:return False
    inputs=[json.loads(x) for x in loaded['input'][1].splitlines() if x.strip()]
    if request not in inputs or len({x['custom_id'] for x in inputs})!=len(inputs):return False
    job=json.loads(loaded['job'][1]);state=json.loads(loaded['state'][1])
    if job.get('status')!='completed' or job.get('endpoint')!=request['url'] or not job.get('output_file_id'):return False
    matches=[x for x in state['jobs'] if x.get('batch_id')==job['id']]
    if len(matches)!=1:return False
    receipt=matches[0]
    if receipt.get('file_id')!=job.get('input_file_id') or receipt.get('input_sha256')!=sha256(loaded['input'][1]).hexdigest():return False
    if receipt.get('requests')!=len(inputs) or job['request_counts']['total']!=len(inputs):return False
    outputs=[json.loads(x) for x in loaded['output'][1].splitlines() if x.strip()]
    if len({x.get('custom_id') for x in outputs})!=len(outputs):return False
    if not {x.get('custom_id') for x in outputs}<={x['custom_id'] for x in inputs}:return False
    found=[x for x in outputs if x.get('custom_id')==request['custom_id']]
    if len(found)!=1 or found[0]!=response:return False
    result=response.get('response',{})
    if response.get('error') or result.get('status_code')!=200 or not result.get('request_id'):return False
    return (reading.get('batch_id')==job['id'] and reading.get('custom_id')==request['custom_id']
            and reading.get('request_id')==result['request_id'])

def verify_sync_binding(proof, request, response, reading):
    """Verify sealed synchronous provenance without relabelling older receipts."""
    from backend.luna_application import request_key
    from backend.luna_reader import usage_cost, MODEL
    from decimal import Decimal
    from backend.luna_budget import money
    records=reading['sync_evidence']
    loaded={name:read_artifact(records[name]) for name in
            ('manifest','authorization','intent','receipt','request','response')}
    value={name:json.loads(data) for name,(_,data) in loaded.items()}
    auth=value['authorization'];manifest=value['manifest'];body=request.get('body',request)
    if auth.get('explicit_user_approval') is not True or auth.get('model')!=MODEL or auth.get('mode')!='sync':return False
    if not str(auth.get('scope','')).strip() or money(auth.get('max_usd',0))<=0:return False
    if auth.get('allow_definitive_950') is not False:return False
    if auth.get('sealed_manifest_sha256')!=sha256(loaded['manifest'][1]).hexdigest():return False
    if Path(auth.get('manifest_path','')).resolve()!=loaded['manifest'][0].resolve():return False
    if value['request']!={'endpoint':'responses','body':body} or value['response']!=response:return False
    rows=manifest.get('requests',[])
    matches=[r for r in rows if r.get('body')==body and r.get('endpoint') in ('responses','/v1/responses')]
    if len(matches)!=1 or auth.get('max_requests',0)<len(rows):return False
    key,_=request_key(body,'responses')
    intent=value['intent'];receipt=value['receipt']
    if intent.get('request_sha256')!=key or intent.get('endpoint')!='responses':return False
    if receipt.get('request_sha256')!=key or receipt.get('response_sha256')!=sha256(loaded['response'][1]).hexdigest():return False
    if receipt.get('mode')!='sync' or receipt.get('http_status')!=200 or not receipt.get('remote_request_id'):return False
    if receipt.get('endpoint')!='responses' or receipt.get('model')!=MODEL:return False
    if response.get('model')!=MODEL or receipt.get('response_id')!=response.get('id') or not response.get('id'):return False
    cost=usage_cost(response,'sync')
    if money(receipt.get('actual_usd'))!=cost or cost>money(intent.get('reserved_usd',0)):return False
    private=Path(auth.get('private_directory','')).resolve()
    for name,suffix in (('intent','.intent.json'),('receipt','.receipt.json'),('request','.request.json'),('response','.response.json')):
        if loaded[name][0].resolve()!=private/(key+suffix):return False
    return request.get('url')=='/v1/responses' and request.get('method')=='POST'


def expected_body(provider, code, stage, ctx, defs):
    """Regenerate the actual provider request, including schema and output cap."""
    content=dict(conversation=ctx.payload(),predicates=defs,
        official_questions={code:provider.contracts[code]['official_question']['text']},
        official_gates={code:provider.contracts[code]['applicability']['text']},external_attestations=[])
    captured=[]
    from backend.luna_reader import LunaProvider
    def capture(body, endpoint):
        captured.append((body,endpoint));raise RuntimeError('offline_capture')
    p=LunaProvider(capture)
    try:p.run(stage,'',content,{},list(defs),{})
    except Exception:
        if not captured:raise
    if len(captured)!=1 or captured[0][1]!='/v1/responses':raise ValueError('unexpected_provider_request')
    return captured[0][0]

def validate_complete_wire(wire,schema):
    from backend.luna_reader import validate_schema
    validate_schema(wire,schema)
    if wire.get('reviewed_entire_context') is not True:
        raise ValueError('qualification_context_not_reviewed')

def verify_certificate(provider,code,proof):
    from backend.luna_reader import MODEL,reader_identity,select_final,validate_schema,SEMANTIC_CLARIFICATIONS,PROMPT,VERIFY
    from crisis_semantic.domain import Input,Turn,digest
    from crisis_semantic.evidence import reconcile
    from crisis_semantic.span_protocol import decode,spans
    from crisis_semantic.scoring import resolve_score
    from backend.evaluators.transversal_candidate_v1.adenda_ri2_v11 import resolve_adenda,final_definitions
    from crisis_semantic.predicate_catalog import definitions
    try:
        if code not in ('CR-RI2','CR-CE10') or not isinstance(proof,dict):return False
        identity=reader_identity(code,provider.contracts)
        if proof.get('identity')!=identity or proof.get('controlled_test_fixture') is not False or proof.get('review_passed') is not True:return False
        refpath=ROOT/'docs/economic_readers_step1_20261015/CASES_REFERENCE_NOT_SENT.json'
        references=json.loads(refpath.read_text(encoding='utf-8'))
        registry={r['case']['id']:r for r in references if code in r['expected']}
        if proof.get('reference_sha256')!=sha256(refpath.read_bytes()).hexdigest():return False
        _,review_bytes=read_artifact(proof['entailment_review'])
        review=json.loads(review_bytes)
        if review.get('review_passed') is not True:return False
        template_path=ROOT/'docs/economic_readers_step1_20261015/BASE_TEMPLATES_NOT_SENT.json'
        templates=json.loads(template_path.read_text(encoding='utf-8'))
        rows=proof.get('cases',[])
        if len(rows)!=len(registry) or {r.get('case_id') for r in rows}!=set(registry):return False
        # Authorization is evidence too: no prospective/zero-budget proposal qualifies.
        auth=proof.get('authorization',{});authpath=Path(auth.get('path',''))
        if not authpath.is_file() or sha256(authpath.read_bytes()).hexdigest()!=auth.get('sha256'):return False
        authorized=json.loads(authpath.read_text(encoding='utf-8-sig'))
        if authorized.get('explicit_user_approval') is not True or float(authorized.get('max_usd',authorized.get('cap_usd',0)))<=0:return False
        defs=final_definitions(definitions(provider.contracts,[code]))
        for r in rows:
            reference=registry[r['case_id']];expected=reference['expected'][code]
            if r.get('expected')!=expected or r.get('actual')!=expected or r.get('literal_and_entailment_reviewed') is not True:return False
            manual=review.get('cases',{}).get(r['case_id'],{})
            if manual.get('passed') is not True or not str(manual.get('reason','')).strip():return False
            readings=r.get('readings',[])
            if len(readings)!=2 or {x.get('stage') for x in readings}!={'extract','verify'} or len({x.get('request_sha256') for x in readings})!=2:return False
            parsed={};contexts=[]
            for x in readings:
                if x.get('model')!=MODEL or x.get('validation_identity')!=identity:return False
                artifacts=x.get('artifacts',[])
                if len(artifacts)!=2 or {a.get('kind') for a in artifacts}!={'request','response'}:return False
                payloads={}
                for a in artifacts:
                    path=Path(a.get('path',''))
                    if not path.is_file() or sha256(path.read_bytes()).hexdigest()!=a.get('sha256'):return False
                    payloads[a['kind']]=json.loads(path.read_text(encoding='utf-8'))
                request=payloads['request'];body=request.get('body',request)
                response=payloads['response'];raw=response.get('response',{}).get('body',response)
                if body.get('model')!=MODEL or digest(body)!=x.get('request_sha256') or not raw.get('usage') or raw['usage'].get('input_tokens',0)<=0:return False
                if body.get('reasoning')!={'effort':'none'} or body.get('store') is not False or 'temperature' in body:return False
                schema=body['text']['format']['schema']
                if digest(schema)!=x.get('schema_sha256'):return False
                c=json.loads(body['input'][1]['content']);q=c['conversation'];case=reference['case']
                original=next(t for t in templates if t['case_id']==r['case_id'] and t['stage']==x['stage'])
                original_body=original.get('body',original.get('request',{}).get('body',{}))
                original_q=json.loads(original_body['input'][1]['content'])['conversation']
                if q!=original_q:return False
                # The candidate cannot qualify on a different conversation with the same label.
                if q['current_user']!=case['current_user'] or q['current_ai']!=case['current_ai'] or q['current_turn']!=case['current_turn']:return False
                history=[{k:v for k,v in h.items() if k!='index'} for h in q['history']]
                if history!=case['history'] or c['predicates']!=defs:return False
                ctx=Input(Turn(q['current_turn'],q['current_user'],q['current_ai'],q['model_evaluated']),tuple(Turn(h['number'],h['user'],h['ai'],h['model']) for h in history))
                if c['literal_spans']!=spans(ctx):return False
                expected_request=expected_body(provider,code,x['stage'],ctx,defs)
                supplied=dict(body);regenerated=dict(expected_request)
                supplied['input']=[dict(item) for item in body['input']]
                regenerated['input']=[dict(item) for item in expected_request['input']]
                # JSON member order is not a semantic configuration difference.
                supplied['input'][1]['content']=json.loads(supplied['input'][1]['content'])
                regenerated['input'][1]['content']=json.loads(regenerated['input'][1]['content'])
                if supplied!=regenerated:return False
                if request.get('url')!='/v1/responses' or request.get('method')!='POST':return False
                if 'sync_evidence' in x:
                    if not verify_sync_binding(proof,request,response,x):return False
                elif not verify_batch_binding(proof,request,response,x):return False
                wire,_=select_final(raw);validate_complete_wire(wire,schema)
                parsed[x['stage']]=decode(wire,c['literal_spans'],defs);contexts.append(ctx)
                reviewed=[v for v in manual.get('observations',[]) if v.get('stage')==x['stage']]
                if len(reviewed)!=len(defs) or {v.get('id') for v in reviewed}!=set(defs):return False
                claims={v['id']:v for v in parsed[x['stage']]['claims']}
                for v in reviewed:
                    if v.get('state')!=claims[v['id']]['state'] or v.get('literal_sources_checked') is not True or v.get('entailment_reviewed') is not True or not str(v.get('reason','')).strip():return False
            if contexts[0]!=contexts[1]:return False
            values,decisions,issues=reconcile(parsed['extract'],parsed['verify'],defs,contexts[0])
            local={k.split('.',1)[1]:v for k,v in values.items()}
            gate=(len(contexts[0].history)>=2) if code=='CR-CE10' else local.get('gate')
            if expected is None:
                if gate is not False:return False
            else:
                if gate is not True:return False
                actual,_=resolve_adenda(code,local,provider.contracts) if code=='CR-RI2' else resolve_score(code,local,provider.contracts)
                if actual!=expected:return False
        return True
    except (KeyError,TypeError,ValueError,OSError,AttributeError,RuntimeError,StopIteration,IndexError,OverflowError):return False
