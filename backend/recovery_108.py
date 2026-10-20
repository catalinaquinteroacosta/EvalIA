"""Candidate recovery transport; never mounted in production by this module.
Original semantic bodies/scorers/runtime remain untouched. Separate execution grant.
"""
import os,json
from pathlib import Path
from hashlib import sha256
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from backend.luna_sequential import SequentialTransport
from backend.luna_application import request_key
from backend.luna_budget import BudgetBlocked,money
from backend import luna_reader as reader,luna_sync_runtime as sync

KEY='b43b84dfa22e600ec9c630ea58ecc44c325628e104376f7eb8521ba555f943cd'
MAX='0.092545'
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def hashed(p):return sha256(Path(p).read_bytes()).hexdigest()
def sealed(p,obj):
    data=json.dumps(obj,ensure_ascii=False,sort_keys=True).encode()
    if p.exists():
        if p.read_bytes()!=data:raise BudgetBlocked('recovery_seal_changed')
    else:sync.write_once(p,data)

def inspect_recovery(authorization_path,grant_path):
    """Read-only status; polling never reconciles or reserves money."""
    auth=read(authorization_path);g=read(grant_path);root=Path(auth['private_directory']);original=root/KEY
    if g.get('request_sha256')!=KEY or g.get('experiment_id')!=108 or g.get('max_total_usd')!='3.00' or g.get('replacement_max_usd')!=MAX or g.get('max_replacements')!=1 or g.get('parent_manifest_sha256')!=auth['sealed_manifest_sha256'] or money(auth['max_usd'])!=3:raise BudgetBlocked('invalid_recovery_status_scope')
    for suffix in ('intent','failure'):
        if hashed(original/(KEY+'.'+suffix+'.json'))!=g['original_'+suffix+'_sha256']:raise BudgetBlocked('original_uncertainty_changed')
    entry=read(auth['budget_journal'])['entries'][auth['run_id']+'_'+KEY]
    if entry['status']!='uncertain' or money(entry['reservation_usd'])!=money(MAX):raise BudgetBlocked('original_reserve_changed')
    failures=[p for p in root.rglob('*.failure.json') if p!=original/(KEY+'.failure.json')]
    pending=[p for p in root.rglob('*.intent.json') if p!=original/(KEY+'.intent.json') and not p.with_name(p.name.replace('.intent.json','.receipt.json')).exists()]
    recoverable=0
    for intent in pending:
        key=intent.name.removesuffix('.intent.json');folder=intent.parent
        try:
            raw=read(folder/(key+'.response.json'));headers=read(folder/(key+'.headers.json'));child=read(folder/'authorization.json')
            manifest=read(folder/'manifest.json');row=manifest['requests'][0]
            actual_key,wire=request_key(row['body'],row['endpoint'])
            if actual_key==key and hashed(folder/'manifest.json')==child['sealed_manifest_sha256'] and (folder/(key+'.request.json')).read_bytes()==wire and headers['http_status']==200 and raw.get('model')==reader.MODEL and reader.usage_cost(raw,'sync')<=money(child['max_usd']):recoverable+=1
        except (OSError,KeyError,ValueError,TypeError):pass
    return dict(execution_approved=g.get('execution_approved') is True and g.get('installation_approved') is True,new_uncertain_requests=len(pending),locally_recoverable_requests=recoverable,new_failure_paths=failures)

class RecordedSync(sync.SealedSyncTransport):
    """Same sealed synchronous request, with durable phases and early headers."""
    def __init__(self,authorization_path):
        super().__init__(authorization_path)
        # Recover a valid response already fsynced before a crash, without another send.
        for key,(_,endpoint,_,reserve) in self.requests.items():
            raw=self.root/(key+'.response.json');receipt=self.root/(key+'.receipt.json');headers=self.root/(key+'.headers.json')
            if raw.exists() and not receipt.exists() and headers.exists():
                info=read(headers);parsed=read(raw)
                if info.get('http_status')!=200 or parsed.get('model')!=reader.MODEL:raise BudgetBlocked('unverified_partial_response')
                cost=reader.usage_cost(parsed,'sync')
                if cost>reserve:raise BudgetBlocked('partial_response_cost_exceeds_reserve')
                sealed(receipt,dict(request_sha256=key,response_sha256=hashed(raw),response_id=parsed.get('id'),actual_usd=str(cost),mode='sync',endpoint=endpoint,model=reader.MODEL,http_status=200,request_id=info.get('remote_request_id'),remote_request_id=info.get('remote_request_id')))
                self.journal.settle(self.run,actual_usd=str(cost),actual_requests=1,usage_evidence=str(self.root),fully_reconciled=True)
    def _open_observed(self,request,key):
        from backend.phase_http import PhaseLog,open_request_observed
        log=PhaseLog(self.root/(key+'.transport.jsonl'),key)
        return open_request_observed(request,log,opener_factory=getattr(self,'opener_factory',None))

    def __call__(self,body,endpoint):
        key,wire=request_key(body,endpoint)
        if key not in self.requests or self.requests[key][2]!=wire:raise BudgetBlocked('recorded_outside_scope')
        reserve=self.requests[key][3]
        with self.lock:
            result=self.root/(key+'.response.json');receipt=self.root/(key+'.receipt.json');intent=self.root/(key+'.intent.json')
            if result.exists() and receipt.exists():
                proof=read(receipt)
                if proof['request_sha256']!=key or hashed(result)!=proof['response_sha256']:raise BudgetBlocked('recorded_receipt_changed')
                return read(result)
            if intent.exists() or list(self.root.glob('*.failure.json')):raise BudgetBlocked('recorded_uncertain_no_retry')
            if self.journal.snapshot()['blocked']:raise BudgetBlocked('budget_globally_blocked')
            # Everything that can be confirmed as pre-send happens before intent.
            secret=os.environ.get('OPENAI_API_KEY')
            if not secret:raise BudgetBlocked('confirmed_pre_send_missing_credential')
            request=Request('https://api.openai.com/v1/'+endpoint,data=json.dumps(body,ensure_ascii=False).encode(),method='POST',headers={'Authorization':'Bearer '+secret,'Content-Type':'application/json'})
            project=os.environ.get('OPENAI_PROJECT')
            if project:
                import re
                if not re.fullmatch(r'proj_[A-Za-z0-9_-]+',project):raise BudgetBlocked('confirmed_pre_send_invalid_project')
                request.add_header('OpenAI-Project',project)
            if not (self.root/(key+'.request.json')).exists():sync.write_once(self.root/(key+'.request.json'),wire)
            sealed(intent,dict(request_sha256=key,endpoint=endpoint,reserved_usd=str(reserve)))
            try:
                with self._open_observed(request,key) as response:
                    headers=getattr(response,'headers',{})
                    info=dict(http_status=getattr(response,'status',None),remote_request_id=headers.get('x-request-id'),phase='headers_received')
                    sealed(self.root/(key+'.headers.json'),info) # durable even if read() times out
                    raw=response.read()
                sync.write_once(result,raw)
                parsed=json.loads(raw)
                if parsed.get('model')!=reader.MODEL:raise ValueError('recorded_model_mismatch')
                cost=reader.usage_cost(parsed,'sync')
                if cost>reserve:raise BudgetBlocked('recorded_cost_exceeds_reservation')
                proof=dict(request_sha256=key,response_sha256=sha256(raw).hexdigest(),response_id=parsed.get('id'),actual_usd=str(cost),mode='sync',endpoint=endpoint,model=reader.MODEL,http_status=info['http_status'],request_id=info['remote_request_id'],remote_request_id=info['remote_request_id'])
                sealed(receipt,proof)
                self.journal.settle(self.run,actual_usd=str(cost),actual_requests=1,usage_evidence=str(self.root),fully_reconciled=True)
                return parsed
            except Exception as error:
                failure=dict(error_type=type(error).__name__,request_sha256=key,transmission_status='uncertain_no_retry',phase='headers_received' if (self.root/(key+'.headers.json')).exists() else 'dispatch_started')
                if isinstance(error,HTTPError):
                    failure.update(http_status=error.code,remote_request_id=error.headers.get('x-request-id'),phase='http_error_received')
                if (self.root/(key+'.headers.json')).exists():failure.update(read(self.root/(key+'.headers.json')))
                phases=self.root/(key+'.transport.jsonl')
                if phases.exists():
                    records=[json.loads(line) for line in phases.read_text(encoding='utf8').splitlines()]
                    diagnostic=next((r for r in reversed(records) if r['phase']=='failure'),{})
                    for field in ('reason_type','errno','winerror','tls_verify_code','classification','failed_phase'):
                        if field in diagnostic:failure[field]=diagnostic[field]
                sealed(self.root/(key+'.failure.json'),failure)
                self.journal.mark_uncertain(self.run,reason='recorded_failure_no_retry:'+key)
                raise RuntimeError('recorded_uncertain_reserved_no_retry') from None

class Recovery108(SequentialTransport):
    def __init__(self,authorization_path,grant_path):
        super().__init__(authorization_path)
        self.grant_path=Path(grant_path);self.grant=read(self.grant_path)
        g=self.grant
        if g.get('request_sha256')!=KEY or g.get('experiment_id')!=108 or g.get('replacement_max_usd')!=MAX or g.get('max_replacements')!=1 or g.get('parent_manifest_sha256')!=self.config['sealed_manifest_sha256'] or g.get('max_total_usd')!='3.00':raise BudgetBlocked('recovery_grant_scope_invalid')
        self.original=self.root/KEY;self.replacement=self.root/'replacement-123-1'/KEY
        for suffix in ('intent','failure'):
            if hashed(self.original/(KEY+'.'+suffix+'.json'))!=g['original_'+suffix+'_sha256']:raise BudgetBlocked('original_uncertainty_changed')
        if (self.original/(KEY+'.receipt.json')).exists():raise BudgetBlocked('original_now_has_receipt_reconcile_first')
        entry=self.journal._load()['entries'].get(self.config['run_id']+'_'+KEY)
        if not entry or entry['status']!='uncertain' or money(entry['reservation_usd'])!=money(MAX):raise BudgetBlocked('original_reserve_not_preserved')
        # Restore only verified newly persisted response artifacts, never retry.
        for raw in self.root.rglob('*.response.json'):
            key=raw.name.removesuffix('.response.json')
            if not raw.with_name(key+'.receipt.json').exists():
                if raw.parent==self.original:raise BudgetBlocked('original_artifact_requires_separate_reconciliation')
                RecordedSync(raw.parent/'authorization.json')
        # Reconcile a replacement receipt persisted just before a process crash.
        receipt=self.replacement/(KEY+'.receipt.json')
        if receipt.exists():
            self.cached(self.replacement,KEY)
            child=read(self.replacement/'authorization.json')
            entry=self.journal._load()['entries'][child['run_id']]
            if entry['status']!='settled':self.journal.settle(child['run_id'],actual_usd=read(receipt)['actual_usd'],actual_requests=1,usage_evidence=str(self.replacement),fully_reconciled=True)
            elif money(entry['actual_usd'])!=money(read(receipt)['actual_usd']):raise BudgetBlocked('replacement_settled_cost_mismatch')
    def cached(self,folder,key):
        receipt=folder/(key+'.receipt.json');raw=folder/(key+'.response.json');proof=read(receipt)
        if proof['request_sha256']!=key or hashed(raw)!=proof['response_sha256']:raise BudgetBlocked('recovery_receipt_changed')
        return read(raw)
    def assert_continuable(self):
        for suffix in ('intent','failure'):
            if hashed(self.original/(KEY+'.'+suffix+'.json'))!=self.grant['original_'+suffix+'_sha256']:raise BudgetBlocked('original_uncertainty_changed')
        for p in self.root.rglob('*.intent.json'):
            if p==self.original/(KEY+'.intent.json'):continue
            if not p.with_name(p.name.replace('.intent.json','.receipt.json')).exists():raise BudgetBlocked('recovery_new_uncertain_no_retry')
        for p in self.root.rglob('*.failure.json'):
            if p!=self.original/(KEY+'.failure.json'):raise BudgetBlocked('recovery_new_failure_requires_review')
    def __call__(self,body,endpoint):
        key=request_key(body,endpoint)[0]
        if key not in self.requests or self.requests[key]['body']!=body:raise BudgetBlocked('recovery_body_changed')
        with self.lock:
            folder=self.replacement if key==KEY else self.root/key
            if (folder/(key+'.receipt.json')).exists():return self.cached(folder,key)
            self.assert_continuable()
            # Preparation authorization never permits transmission.
            current=read(self.grant_path)
            if current!=self.grant or current.get('execution_approved') is not True or current.get('installation_approved') is not True:raise BudgetBlocked('separate_execution_and_installation_approval_required')
            cap=reader.estimate_reserve(body,'sync')['reserved_usd']
            if key==KEY and money(cap)>money(MAX):raise BudgetBlocked('replacement_reserve_exceeds_approval')
            if not os.environ.get('OPENAI_API_KEY'):raise BudgetBlocked('confirmed_pre_send_missing_credential')
            folder.mkdir(parents=True,exist_ok=True)
            manifest={**self.manifest,'requests':[self.requests[key]]}
            if key==KEY:manifest['replacement_lineage']=dict(original_request_sha256=KEY,attempt='replacement-123-1',original_intent_sha256=self.grant['original_intent_sha256'])
            sealed(folder/'manifest.json',manifest)
            auth={**self.config,'manifest_path':str((folder/'manifest.json').resolve()),'sealed_manifest_sha256':hashed(folder/'manifest.json'),'private_directory':str(folder.resolve()),'run_id':self.config['run_id']+'_'+key+('_replacement_1' if key==KEY else ''),'max_requests':1,'max_usd':cap}
            sealed(folder/'authorization.json',auth)
            raw=RecordedSync(folder/'authorization.json')(body,endpoint)
            return raw
