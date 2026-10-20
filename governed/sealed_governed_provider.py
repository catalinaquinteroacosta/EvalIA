"""Explicit future real connector. No network/credential access on import/init.
Uses the installed recovery transport and an inner per-request journal; the
coordinator ledger alone is summed globally (never add mirrored inner ledgers).
"""
import json,hashlib,os
from pathlib import Path
class SealedGovernedProvider:
    simulation_only=False
    def __init__(self,lab,job,authorization_path,private_root):
        self.lab=lab;self.job=job;self.root=Path(private_root)
        self.auth=json.loads(Path(authorization_path).read_text(encoding='utf8'))
        raw=Path(self.auth['manifest_path']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=self.auth['sealed_manifest_sha256'] or self.auth.get('explicit_user_approval') is not True:raise ValueError('sealed scoped authorization required')
        self.manifest=json.loads(raw);self.requests={};self.prepared={}
        for row in self.manifest['requests']:
            body=json.dumps(row['body'],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode();self.requests[hashlib.sha256(body).hexdigest()]=row
        c=lab.connect()
        try:
            jobrow=c.execute('SELECT experiment FROM jobs WHERE id=?',(job,)).fetchone()
            keys={r[0] for r in c.execute('SELECT key FROM requests WHERE job=?',(job,))}
            if not jobrow or self.auth['allowed_experiment_ids']!=[jobrow[0]] or keys!=set(self.requests):raise ValueError('job/manifest scope mismatch')
        finally:c.close()
    def request_folder(self,key):
        from historical_recovery_gate import check
        identity=check(self.lab,self.job,key)
        # Identity is hashed for a safe path; the signed decision retains its text.
        base=self.root/key if identity is None else self.root/key/('replacement-'+hashlib.sha256(identity.encode()).hexdigest())
        from continuity import attempt
        ordinal,_=attempt(self.lab,key)
        return base if ordinal==0 else base/('attempt-'+str(ordinal).zfill(4))
    def reconcile_no_send(self,key):
        from backend.reconcile_no_send import reconcile
        from backend.luna_application import request_key
        from continuity import attempt
        folder=self.request_folder(key);row=self.requests[key];native,wire=request_key(row['body'],row['endpoint'])
        if not (folder/(native+'.failure.json')).exists():return None
        failure=json.loads((folder/(native+'.failure.json')).read_text(encoding='utf8'))
        if failure.get('classification')!='confirmed_no_api_send':return None
        manifest=json.loads((folder/'manifest.json').read_text(encoding='utf8'))
        if manifest['requests']!=[row] or (folder/(native+'.request.json')).read_bytes()!=wire:raise ValueError('foreign no-send body')
        reconcile(folder) # validates phases/auth and idempotently settles inner mirror
        hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.suffix in ('.json','.jsonl') and p.name!='inner-budget.json'}
        return dict(classification='confirmed_no_api_send',verified_native_proof=True,request_body_key=key,ordinal=attempt(self.lab,key)[0],folder=str(folder.resolve()),evidence_sha256=hashes)
    def prepare(self,body):
        key=hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
        if key not in self.requests or body!=self.requests[key]['body']:raise ValueError('body outside grant')
        if not os.environ.get('OPENAI_API_KEY'):raise RuntimeError('confirmed pre-send missing credential')
        from backend import luna_reader as reader
        from backend.luna_budget import BudgetJournal
        from backend.recovery_108 import RecordedSync,sealed,read
        if self.lab.policy()['mode']!='real':raise ValueError('real transport not activated')
        c=self.lab.connect()
        try:
            row=c.execute('SELECT job,status FROM requests WHERE key=?',(key,)).fetchone()
            if not row or row['job']!=self.job or row['status']!='reserved':raise ValueError('coordinator reservation required before preflight')
        finally:c.close()
        # Credential is loaded only by the explicitly activated Windows worker.
        if not os.environ.get('OPENAI_API_KEY'):raise RuntimeError('credential unavailable; no HTTP attempted')
        folder=self.request_folder(key);folder.mkdir(parents=True,exist_ok=True)
        manifest={**self.manifest,'requests':[self.requests[key]],'coordinator_job':self.job}
        sealed(folder/'manifest.json',manifest)
        cap=reader.estimate_reserve(body,'sync')['reserved_usd'];journal=BudgetJournal(folder/'inner-budget.json')
        journal.initialize(cap_usd=cap,prior_evidence='Mirror of already reserved coordinator request '+key+'; not additional authorization')
        auth={**self.auth,'manifest_path':str((folder/'manifest.json').resolve()),'sealed_manifest_sha256':hashlib.sha256((folder/'manifest.json').read_bytes()).hexdigest(),'private_directory':str(folder.resolve()),'budget_journal':str((folder/'inner-budget.json').resolve()),'run_id':self.auth['run_id']+'_'+key,'max_requests':1,'max_usd':cap}
        auth['allow_definitive_950']=False
        if folder.name.startswith('replacement-'):
            auth['run_id']+='_'+folder.name
            auth['replacement_decision_identity_sha256']=folder.name.removeprefix('replacement-')
        if folder.name.startswith('attempt-'):
            auth['run_id']+='_'+folder.name
            auth['no_post_retry_attempt']=folder.name
        sealed(folder/'authorization.json',auth)
        self.prepared[key]=RecordedSync(folder/'authorization.json')
    def __call__(self,body):
        from backend.recovery_108 import read
        from backend.luna_application import request_key
        key=hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
        c=self.lab.connect()
        try:row=c.execute('SELECT job,status FROM requests WHERE key=?',(key,)).fetchone()
        finally:c.close()
        if not row or row['job']!=self.job or row['status']!='sending' or key not in self.prepared:raise ValueError('prepared owned intent required')
        folder=self.request_folder(key)
        raw=self.prepared[key](body,self.requests[key]['endpoint'])
        native_key,_=request_key(body,self.requests[key]['endpoint'])
        proof=read(folder/(native_key+'.receipt.json'))
        # File-phase interval: body reception/persistence after durable headers,
        # not provider compute time. Total transport measured by coordinator.
        interval=max(0,((folder/(native_key+'.response.json')).stat().st_mtime_ns-(folder/(native_key+'.headers.json')).stat().st_mtime_ns)/1e9)
        return proof['actual_usd'],raw,dict(response_seconds=interval)

def reconcile_native_receipts(provider,*,fences):
    """Explicit OS-fenced maintenance. No HTTP, no automatic requeue."""
    from supervision import Fence
    maintenance=Fence(Path(fences)/'maintenance.lock');held=[]
    if not maintenance.acquire():raise ValueError('maintenance busy')
    try:
        for job in provider.lab.snapshot()['jobs']:
            f=Fence(Path(fences)/(job['id']+'.worker.lock'))
            if not f.acquire():raise ValueError('worker still active; do not reconcile')
            held.append(f)
        return _reconcile_native_receipts(provider)
    finally:
        for f in reversed(held):f.release()
        maintenance.release()

def _reconcile_native_receipts(provider):
    from backend.recovery_108 import RecordedSync,read,hashed
    from backend.luna_application import request_key
    recovered=0
    for key,row in provider.requests.items():
        # Completed substitutions keep their distinct folder even after the gate
        # no longer requires approval for receipt replay.
        c=provider.lab.connect()
        try:
            exists=c.execute("SELECT 1 FROM sqlite_master WHERE name='replacement_decisions'").fetchone()
            decision=c.execute('SELECT identity FROM replacement_decisions WHERE job=? AND key=?',(provider.job,key)).fetchone() if exists else None
        finally:c.close()
        folder=provider.root/key
        if decision:folder=folder/('replacement-'+hashlib.sha256(decision[0].encode()).hexdigest())
        from continuity import attempt
        ordinal,_=attempt(provider.lab,key)
        if ordinal:folder=folder/('attempt-'+str(ordinal).zfill(4))
        native_key,wire=request_key(row['body'],row['endpoint'])
        raw_path=folder/(native_key+'.response.json')
        if not raw_path.exists():
            phases=folder/(native_key+'.transport.jsonl')
            failure=folder/(native_key+'.failure.json')
            if phases.exists() and failure.exists():
                # Authenticated phase evidence, not exception-name inference.
                from continuity import record_no_send
                try:proof=provider.reconcile_no_send(key)
                except (ValueError,KeyError,OSError):continue
                if proof:record_no_send(provider.lab,provider.job,key,proof)
            continue
        c=provider.lab.connect()
        try:r=c.execute('SELECT job,status FROM requests WHERE key=?',(key,)).fetchone()
        finally:c.close()
        if not r or r['job']!=provider.job:raise ValueError('foreign recovery receipt')
        if r['status']=='completed':continue
        if r['status'] not in ('uncertain','sending'):raise ValueError('unexpected recovery phase')
        if (folder/(native_key+'.request.json')).read_bytes()!=wire:raise ValueError('native request changed')
        # Constructor only validates/reconciles fsynced responses; __call__ is NOT used.
        RecordedSync(folder/'authorization.json')
        proof=read(folder/(native_key+'.receipt.json'))
        if proof['request_sha256']!=native_key or proof['response_sha256']!=hashed(raw_path):raise ValueError('native recovery hash mismatch')
        provider.lab.receipt(key,proof['actual_usd'],read(raw_path));recovered+=1
    return recovered
