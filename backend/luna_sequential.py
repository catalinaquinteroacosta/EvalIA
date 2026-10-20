"""Per-request durable reservation over unchanged sealed semantic bodies."""
import json
from pathlib import Path
from hashlib import sha256
from backend.luna_application import ProcessLock,request_key
from backend.luna_budget import BudgetJournal,BudgetBlocked,money
from backend import luna_reader,luna_runner,luna_sync_runtime as sync

def read_child_run(folder):
    return json.loads((folder/'authorization.json').read_text(encoding='utf8'))['run_id']

class SequentialTransport:
    def __init__(self,authorization_path):
        self.config=json.loads(Path(authorization_path).read_text(encoding='utf8'));c=self.config
        raw=Path(c['manifest_path']).read_bytes();self.manifest=json.loads(raw)
        if sha256(raw).hexdigest()!=c['sealed_manifest_sha256']:raise BudgetBlocked('sequential_manifest_changed')
        if c.get('execution_policy')!='sequential_per_request' or c.get('explicit_user_approval') is not True or c.get('allowed_experiment_ids')!=[108] or not 0<money(c['max_usd'])<=3:raise BudgetBlocked('sequential_authorization_invalid')
        if c['max_requests']!=len(self.manifest['requests']):raise BudgetBlocked('sequential_count_changed')
        self.requests={request_key(r['body'],r['endpoint'])[0]:r for r in self.manifest['requests']}
        if len(self.requests)!=c['max_requests']:raise BudgetBlocked('duplicate_sequential_body')
        self.root=Path(c['private_directory']);self.root.mkdir(parents=True,exist_ok=True)
        self.lock=ProcessLock(self.root/'.sequential.lock');self.journal=BudgetJournal(c['budget_journal'])
        if self.journal.path.exists():
            if money(self.journal.snapshot()['cap_usd'])!=money(c['max_usd']):raise BudgetBlocked('sequential_journal_cap_changed')
        else:self.journal.initialize(cap_usd=c['max_usd'],prior_evidence='Explicit sequential plan '+c['run_id'])
        expected={name:sha256(Path(mod.__file__).read_bytes()).hexdigest() for name,mod in [('luna_reader',luna_reader),('luna_runner',luna_runner),('luna_sync_runtime',sync)]}
        if self.manifest['runtime_sources']!=expected:raise BudgetBlocked('sequential_runtime_changed')
        # A crash after receipt persistence but before settlement must not strand funds.
        with self.journal.lock:
            pending={key for key,row in self.journal._load()['entries'].items() if row['status']!='settled'}
        for receipt in self.root.rglob('*.receipt.json') if pending else ():
            proof=json.loads(receipt.read_text(encoding='utf8'));folder=receipt.parent
            if read_child_run(folder) not in pending:continue
            key=proof['request_sha256'];raw=(folder/(key+'.response.json')).read_bytes()
            if key not in self.requests or sha256(raw).hexdigest()!=proof['response_sha256']:raise BudgetBlocked('sequential_receipt_corrupted')
            child=json.loads((folder/'authorization.json').read_text(encoding='utf8'))
            self.journal.settle(child['run_id'],actual_usd=proof['actual_usd'],actual_requests=1,usage_evidence=str(folder.resolve()),fully_reconciled=True)

    def __call__(self,body,endpoint):
        key=request_key(body,endpoint)[0]
        if key not in self.requests or self.requests[key]['body']!=body:raise BudgetBlocked('outside_sequential_scope')
        with self.lock:
            cached=self.root/key/(key+'.receipt.json')
            if cached.exists():
                proof=json.loads(cached.read_text(encoding='utf8'))
                raw=cached.with_name(key+'.response.json').read_bytes()
                if proof['request_sha256']!=key or proof['response_sha256']!=sha256(raw).hexdigest():raise BudgetBlocked('sequential_replay_corrupted')
                return json.loads(raw)
            # An interrupted intent anywhere stops the complete plan, even after restart.
            for p in self.root.rglob('*.intent.json'):
                if not p.with_name(p.name.replace('.intent.json','.receipt.json')).exists():raise BudgetBlocked('sequential_uncertain_no_retry')
            folder=self.root/key;folder.mkdir(exist_ok=True)
            manifest={**self.manifest,'requests':[self.requests[key]]}
            def sealed(path,obj):
                data=json.dumps(obj,ensure_ascii=False,sort_keys=True).encode()
                if path.exists():
                    if path.read_bytes()!=data:raise BudgetBlocked('sequential_child_seal_changed')
                else:sync.write_once(path,data)
            sealed(folder/'manifest.json',manifest)
            cap=luna_reader.estimate_reserve(body,'sync')['reserved_usd']
            authorization={**self.config,'manifest_path':str((folder/'manifest.json').resolve()),'sealed_manifest_sha256':sha256((folder/'manifest.json').read_bytes()).hexdigest(),'private_directory':str(folder.resolve()),'run_id':self.config['run_id']+'_'+key,'max_requests':1,'max_usd':cap}
            sealed(folder/'authorization.json',authorization)
            # Shared journal reserves before network, settles this request only.
            transport=sync.SealedSyncTransport(folder/'authorization.json')
            raw=transport(body,endpoint)
            receipt=json.loads((folder/(key+'.receipt.json')).read_text(encoding='utf8'))
            self.journal.settle(authorization['run_id'],actual_usd=receipt['actual_usd'],actual_requests=1,usage_evidence=str(folder.resolve()),fully_reconciled=True)
            return raw
