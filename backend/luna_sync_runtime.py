"""Opt-in, sealed-request synchronous transport. No network on configuration.

Authorization is server-side and grants only exact request bodies. There is no
fallback to Batch, retry, broader experiment, or a different reader identity.
"""
import json
import os
from hashlib import sha256
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from backend.luna_application import ProcessLock, request_key
from backend.luna_budget import BudgetJournal, BudgetBlocked, money


def write_once(path, data):
    with path.open('xb') as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())


class SealedSyncTransport:
    def __init__(self, authorization_path):
        from backend import luna_reader
        self.config=json.loads(Path(authorization_path).read_text(encoding='utf-8'))
        c=self.config
        if c.get('mode')!='sync' or c.get('model')!=luna_reader.MODEL or c.get('explicit_user_approval') is not True:
            raise BudgetBlocked('explicit_luna_sync_authorization_required')
        if not c.get('allowed_experiment_ids') or any(type(i) is not int or i<=0 for i in c['allowed_experiment_ids']):
            raise BudgetBlocked('explicit_experiment_scope_required')
        path=Path(c['manifest_path']).resolve(); raw=path.read_bytes()
        if sha256(raw).hexdigest()!=c.get('sealed_manifest_sha256'):
            raise BudgetBlocked('sealed_manifest_hash_mismatch')
        manifest=json.loads(raw)
        if manifest.get('reader_sha256')!=sha256(Path(luna_reader.__file__).read_bytes()).hexdigest():
            raise BudgetBlocked('sealed_reader_identity_mismatch')
        from backend import luna_runner
        expected_sources={name:sha256(Path(module.__file__).read_bytes()).hexdigest()
            for name,module in (('luna_reader',luna_reader),('luna_runner',luna_runner))}
        expected_sources['luna_sync_runtime']=sha256(Path(__file__).read_bytes()).hexdigest()
        if manifest.get('runtime_sources')!=expected_sources:
            raise BudgetBlocked('sealed_runtime_source_identity_mismatch')
        if manifest.get('allowed_experiment_ids')!=c['allowed_experiment_ids']:
            raise BudgetBlocked('sealed_experiment_scope_mismatch')
        self.requests={}
        total=money(0)
        for row in manifest['requests']:
            body=row['body']; endpoint=row['endpoint'].removeprefix('/v1/')
            if endpoint not in ('responses','chat/completions') or body.get('model')!=luna_reader.MODEL:
                raise BudgetBlocked('sealed_request_endpoint_or_model_mismatch')
            key,wire=request_key(body,endpoint)
            if key in self.requests:raise BudgetBlocked('duplicate_sealed_request')
            reserve=money(luna_reader.estimate_reserve(body,mode='sync')['reserved_usd'])
            self.requests[key]=(body,endpoint,wire,reserve); total+=reserve
        if not self.requests or len(self.requests)!=c.get('max_requests') or total>money(c.get('max_usd',0)):
            raise BudgetBlocked('sealed_sync_budget_or_count_exceeded')
        self.root=Path(c['private_directory']).resolve(); self.root.mkdir(parents=True,exist_ok=True)
        self.lock=ProcessLock(self.root/'.sync.lock')
        ownership=json.dumps(dict(run_id=c['run_id'],manifest_sha256=c['sealed_manifest_sha256']),sort_keys=True).encode()
        with self.lock:
            owner=self.root/'ownership.json'
            if owner.exists():
                if owner.read_bytes()!=ownership:raise BudgetBlocked('sync_directory_owned_by_another_run')
            else:write_once(owner,ownership)
        self.journal=BudgetJournal(c['budget_journal'])
        self.run=c['run_id']; self.total=total
        self.journal.reserve(self.run,c['sealed_manifest_sha256'],reservation_usd=c['max_usd'],
            requests=len(self.requests),authorization=c,scope=c['scope'])

    def __call__(self,body,endpoint):
        from backend.luna_reader import usage_cost, MODEL
        key,wire=request_key(body,endpoint)
        if key not in self.requests:raise BudgetBlocked('request_outside_sealed_sync_scope')
        expected,endpoint,original,reserve=self.requests[key]
        if wire!=original:raise BudgetBlocked('sealed_sync_request_changed')
        with self.lock:
            result=self.root/(key+'.response.json'); receipt=self.root/(key+'.receipt.json')
            intent=self.root/(key+'.intent.json')
            if result.exists() and receipt.exists():
                proof=json.loads(receipt.read_text(encoding='utf-8')); raw=result.read_bytes()
                if proof['response_sha256']!=sha256(raw).hexdigest() or proof['request_sha256']!=key:
                    raise BudgetBlocked('sync_replay_integrity_failure')
                return json.loads(raw)
            if intent.exists() or any(self.root.glob('*.failure.json')):
                raise BudgetBlocked('uncertain_sync_request_no_retry_or_continuation')
            with self.journal.lock:
                state=self.journal._load(); entry=state['entries'][self.run]
                if self.journal._totals(state)['blocked'] or entry['status']!='reserved':
                    raise BudgetBlocked('sync_budget_not_available_for_transmission')
            secret=os.environ.get('OPENAI_API_KEY')
            if not secret:raise BudgetBlocked('server_api_key_missing')
            write_once(self.root/(key+'.request.json'),wire)
            write_once(intent,json.dumps(dict(request_sha256=key,endpoint=endpoint,reserved_usd=str(reserve))).encode())
            try:
                request=Request('https://api.openai.com/v1/'+endpoint,
                    data=json.dumps(body,ensure_ascii=False).encode(),method='POST',
                    headers={'Authorization':'Bearer '+secret,'Content-Type':'application/json'})
                with urlopen(request,timeout=180) as response:
                    remote_status=getattr(response,'status',None)
                    remote_headers=getattr(response,'headers',{})
                    remote_request_id=remote_headers.get('x-request-id')
                    data=response.read()
                write_once(result,data)  # Preserve original bytes even if validation fails.
                raw=json.loads(data)
                if raw.get('model')!=MODEL:raise ValueError('sync_response_model_mismatch')
                cost=usage_cost(raw,mode='sync')
                if cost>reserve:raise BudgetBlocked('sync_actual_exceeds_request_reserve')
                proof=dict(request_sha256=key,response_sha256=sha256(data).hexdigest(),
                    response_id=raw.get('id'),actual_usd=str(cost),mode='sync',
                    endpoint=endpoint,model=raw.get('model'),http_status=remote_status,
                    request_id=remote_request_id,remote_request_id=remote_request_id)
                write_once(receipt,json.dumps(proof).encode())
                receipts=list(self.root.glob('*.receipt.json'))
                if len(receipts)==len(self.requests):
                    spent=sum((money(json.loads(p.read_text())['actual_usd']) for p in receipts),money(0))
                    self.journal.settle(self.run,actual_usd=spent,actual_requests=len(receipts),
                        usage_evidence=str(self.root),fully_reconciled=True)
                return raw
            except Exception as error:
                failure=dict(error_type=type(error).__name__,request_sha256=key)
                if isinstance(error,URLError) and not isinstance(error,HTTPError):
                    reason=error.reason
                    failure.update(network_reason_type=type(reason).__name__,
                        network_reason=str(reason)[:1024],network_errno=getattr(reason,'errno',None),
                        network_winerror=getattr(reason,'winerror',None),
                        transmission_status='uncertain_no_retry')
                if isinstance(error,HTTPError):
                    error_data=error.read()
                    write_once(self.root/(key+'.http_error.bin'),error_data)
                    failure.update(http_status=error.code,remote_request_id=error.headers.get('x-request-id'),
                        error_body_sha256=sha256(error_data).hexdigest())
                write_once(self.root/(key+'.failure.json'),json.dumps(failure).encode())
                self.journal.mark_uncertain(self.run,reason='sync_failure_no_retry:'+key)
                raise RuntimeError('sync_request_failed_reserved_no_retry') from None

    def close(self):
        pass


def configure(app,authorization_path):
    """Explicit server mount; candidate remains gated by own qualifications."""
    from backend.luna_reader import LunaProvider,read_anxiety
    from backend.luna_runner import IntegrationRunner
    from backend.evaluators.ansiedad_semantic.budgeted_reader import envelope
    transport=SealedSyncTransport(authorization_path)
    certificates={}
    if transport.config.get('certificates_path'):
        certificates=json.loads(Path(transport.config['certificates_path']).read_text(encoding='utf-8'))
    provider=LunaProvider(transport,certificates=certificates)
    def anxiety(request):
        return read_anxiety(request,transport)
    app.state.evaluation_dependencies=dict(runner_factory=IntegrationRunner,
        crisis_provider=provider,anxiety_reader=anxiety,anxiety_model='gpt-6-luna',
        allowed_experiment_ids=frozenset(transport.config['allowed_experiment_ids']),
        evaluation_lock=transport.lock,authorization_id=transport.config['run_id'],paid_mode='sync',paid_submission_enabled=True)
    return transport
