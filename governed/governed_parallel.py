"""Deployment candidate: governed request concurrency over the approved ledger.
Default simulation only. Importing does not load credentials or start workers.
"""
import json,time,hashlib,os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from limited_parallel import ParallelLab
from supervision import Fence

class GovernedLab(ParallelLab):
    def finish_if_complete(self,job,owner):
        with self.tx() as c:
            j=c.execute('SELECT status,owner FROM jobs WHERE id=?',(job,)).fetchone()
            if j['status']=='complete':return True
            if j['status']!='running' or j['owner']!=owner:raise ValueError('foreign completion owner')
            missing=c.execute("SELECT 1 FROM requests WHERE job=? AND status!='completed'",(job,)).fetchone()
            missing_result=c.execute('SELECT 1 FROM response_contracts r WHERE job=? AND NOT EXISTS(SELECT 1 FROM results s WHERE s.job=r.job AND s.response=r.response)',(job,)).fetchone()
            if missing or missing_result:return False
            c.execute("UPDATE jobs SET status='complete',owner=NULL WHERE id=?",(job,));return True
    def create_indexes(self):
        with self.tx() as c:
            c.execute('CREATE INDEX IF NOT EXISTS money_global ON requests(status,actual,reserve)')
            c.execute('CREATE INDEX IF NOT EXISTS money_job ON requests(job,status,actual,reserve)')
            c.execute('CREATE INDEX IF NOT EXISTS ready_job ON requests(job,status,position,key)')
    def persist_result(self,job,response,keys,payload):
        c=self.connect()
        try:
            for key in keys:
                row=c.execute('SELECT body FROM requests WHERE key=? AND job=?',(key,job)).fetchone()
                if not row:raise ValueError('foreign publication key')
                body=json.loads(row[0])
                if 'messages' in body:
                    original=json.loads(body['messages'][1]['content'])['original']
                    if original['model']!=payload.get('model') or original['turn']!=payload.get('turn') or not original['conversation'].startswith(str(payload['experiment'])+':'):raise ValueError('official result context identity differs')
                elif 'input' in body:
                    original=json.loads(body['input'][1]['content'])['conversation']
                    if original['model_evaluated']!=payload.get('model') or original['current_turn']!=payload.get('turn'):raise ValueError('crisis result context identity differs')
        finally:c.close()
        super().persist_result(job,response,keys,payload)
        records=payload.get('result',{}).get('indicator_results',[])
        with self.tx() as c:
            c.execute('CREATE TABLE IF NOT EXISTS response_quality(job TEXT,response TEXT,definitive INTEGER,blocked INTEGER,scored INTEGER,na INTEGER,PRIMARY KEY(job,response))')
            c.execute('INSERT OR IGNORE INTO response_quality VALUES(?,?,?,?,?,?)',(job,str(response),int(bool(records) and all(r['status'] in ('SCORED','N/A') for r in records)),sum(r['status']=='BLOCKED' for r in records),sum(r['status']=='SCORED' for r in records),sum(r['status']=='N/A' for r in records)))
    def initialize(self,cap,workers=2,*,global_requests=2,internal_requests=2):
        if any(type(v)is not int or not 1<=v<=12 for v in (global_requests,internal_requests)):raise ValueError('request limits 1..12')
        super().initialize(cap,workers)
        with self.tx() as c:
            c.executescript('''CREATE TABLE governance(id INTEGER PRIMARY KEY,global_requests INTEGER,internal_requests INTEGER,mode TEXT,rpm INTEGER,tpm INTEGER);
                CREATE TABLE admissions(key TEXT PRIMARY KEY,at REAL,tokens INTEGER);
                CREATE TABLE metrics(job TEXT,key TEXT,stage TEXT,seconds REAL);
                CREATE TABLE grants(job TEXT PRIMARY KEY,explicit_approval INTEGER,grant_hash TEXT);
                CREATE TABLE phases(key TEXT PRIMARY KEY,phase TEXT);''')
            c.execute('INSERT INTO governance VALUES(1,?,?,?,NULL,NULL)',(global_requests,internal_requests,'simulation'))
        self.create_indexes()
    def policy(self):
        c=self.connect()
        try:return dict(c.execute('SELECT * FROM governance').fetchone())
        finally:c.close()
    def authorize_real_job(self,job,grant):
        # A stored balance or simulation enqueue is never a spend grant.
        if grant.get('explicit_user_approval') is not True or grant.get('job')!=job or grant.get('scope')!='exact sealed manifest only':raise ValueError('scoped approval required')
        digest=hashlib.sha256(json.dumps(grant,sort_keys=True).encode()).hexdigest()
        with self.tx() as c:
            row=c.execute('SELECT experiment,cap FROM jobs WHERE id=?',(job,)).fetchone()
            if not row or row['experiment']!=grant.get('experiment'):raise ValueError('grant experiment differs')
            scope=[tuple(r) for r in c.execute('SELECT position,key FROM requests WHERE job=? ORDER BY position',(job,))]
            if grant.get('body_scope_sha256')!=hashlib.sha256(json.dumps(scope).encode()).hexdigest():raise ValueError('exact body scope approval required')
            from queue_lab import units
            if units(grant['max_usd'])!=row['cap']:raise ValueError('grant budget differs')
            prior=c.execute('SELECT grant_hash FROM grants WHERE job=?',(job,)).fetchone()
            if prior and prior[0]!=digest:raise ValueError('cannot replace grant')
            c.execute('INSERT OR IGNORE INTO grants VALUES(?,1,?)',(job,digest))
            c.execute("UPDATE jobs SET status='queued' WHERE id=? AND status='awaiting_authorization'",(job,))
    def configure_governance(self,*,global_requests,internal_requests,mode='simulation',rpm=None,tpm=None,operator_approval=False):
        if any(type(v)is not int or not 1<=v<=12 for v in (global_requests,internal_requests)):raise ValueError('request limits 1..12')
        if mode not in ('simulation','real'):raise ValueError('invalid mode')
        if mode=='real' and (operator_approval is not True or any(type(v)is not int or v<=0 for v in (rpm,tpm))):raise ValueError('verified RPM/TPM and explicit activation required')
        with self.tx() as c:
            if c.execute("SELECT 1 FROM jobs WHERE status='running'").fetchone():raise ValueError('configure only with workers stopped')
            c.execute('UPDATE governance SET global_requests=?,internal_requests=?,mode=?,rpm=?,tpm=? WHERE id=1',(global_requests,internal_requests,mode,rpm,tpm))
    def metric(self,job,key,stage,seconds):
        if stage not in ('queue_wait','quota_wait','transport','response','persistence','scoring'):raise ValueError('unknown timing stage')
        if seconds<0:raise ValueError('negative duration')
        with self.tx() as c:c.execute('INSERT INTO metrics VALUES(?,?,?,?)',(job,key,stage,seconds))
    def quota(self,key,tokens,now=None):
        if type(tokens)is not int or tokens<0:raise ValueError('token upper bound required')
        now=time.time() if now is None else now
        with self.tx() as c:
            p=c.execute('SELECT * FROM governance').fetchone()
            if p['rpm'] is None or p['tpm'] is None:
                if p['mode']=='real':raise ValueError('real quotas unconfigured')
                return True
            if tokens>p['tpm']:raise ValueError('request cannot fit configured TPM')
            old=c.execute('SELECT at FROM admissions WHERE key=?',(key,)).fetchone()
            if old:
                row=c.execute('SELECT status FROM requests WHERE key=?',(key,)).fetchone();phase=c.execute('SELECT phase FROM phases WHERE key=?',(key,)).fetchone()
                if not row or row[0]!='reserved' or phase and phase[0]!='confirmed_pre_send':raise ValueError('request already admitted; no retry')
                if old[0]>now-60:return True
            count,total=c.execute('SELECT count(*),coalesce(sum(tokens),0) FROM admissions WHERE at>?',(now-60,)).fetchone()
            if count>=p['rpm'] or total+tokens>p['tpm']:return False
            c.execute('INSERT OR REPLACE INTO admissions VALUES(?,?,?)',(key,now,tokens));return True
    def execute_batch(self,job,owner,keys,provider,root,*,token_bound=None,fault=None,retain_owner_on_failure=False):
        from continuity import execute
        return execute(self,self._execute_once,job,owner,keys,provider,root,token_bound=token_bound,fault=fault,retain_owner_on_failure=retain_owner_on_failure)
    def _execute_once(self,job,owner,keys,provider,root,*,token_bound=None,fault=None,retain_owner_on_failure=False):
        from historical_recovery_gate import check
        for key in keys:check(self,job,key)
        policy=self.policy();simulation=getattr(provider,'simulation_only',False) is True
        if policy['mode']=='simulation' and not simulation:raise ValueError('real provider forbidden')
        if policy['mode']=='real':
            if simulation or not policy['rpm'] or not policy['tpm']:raise ValueError('real provider/quotas required')
            if not callable(token_bound):raise ValueError('real request token upper bound required')
            c=self.connect();grant=c.execute('SELECT explicit_approval FROM grants WHERE job=?',(job,)).fetchone();c.close()
            if not grant or grant[0]!=1:raise ValueError('job has no spend authorization')
        limit=policy['internal_requests'];rows=self.reserve_batch(job,owner,keys,limit,allow_independent_uncertain=retain_owner_on_failure)
        if not rows:return []
        root=Path(root);root.mkdir(parents=True,exist_ok=True)
        def send(row):
            key=row['key'];body=json.loads(row['body']);began=time.perf_counter();slot=None
            # Reserved while waiting, but not marked sending until admission.
            while slot is None:
                for n in range(policy['global_requests']):
                    f=Fence(root/f'global-slot-{n}.lock')
                    if f.acquire():slot=f;break
                if slot is None:time.sleep(.005)
            self.metric(job,key,'queue_wait',time.perf_counter()-began)
            try:
                began=time.perf_counter()
                tokens=token_bound(body) if token_bound else 0
                if policy['mode']=='real' and tokens<=0:raise ValueError('positive real token upper bound required')
                while not self.quota(key,tokens):time.sleep(.01)
                self.metric(job,key,'quota_wait',time.perf_counter()-began)
                if callable(getattr(provider,'prepare',None)):provider.prepare(body)
                self.mark_sending(key,owner)
                with self.tx() as c:c.execute('INSERT OR REPLACE INTO phases VALUES(?,?)',(key,'dispatch_started'))
                began=time.perf_counter();answer=provider(body);actual,raw=answer[:2];elapsed=time.perf_counter()-began
                self.metric(job,key,'transport',elapsed)
                if len(answer)==3 and answer[2].get('response_seconds') is not None:self.metric(job,key,'response',answer[2]['response_seconds'])
                # Raw response committed before ledger reconciliation.
                proof=dict(key=key,job=job,actual=str(actual),raw=raw)
                wire=json.dumps(proof,sort_keys=True,ensure_ascii=False).encode();path=root/(key+'.durable.json')
                with path.open('xb') as f:f.write(wire);f.flush();os.fsync(f.fileno())
                with path.with_suffix('.sha256').open('x',encoding='ascii') as f:f.write(hashlib.sha256(wire).hexdigest());f.flush();os.fsync(f.fileno())
                if fault:fault('after_response_persisted',key)
                began=time.perf_counter();self.receipt(key,actual,raw)
                self.metric(job,key,'persistence',time.perf_counter()-began)
                with self.tx() as c:c.execute('UPDATE phases SET phase=? WHERE key=?',('receipt_complete',key))
                return dict(key=key,state='completed')
            except Exception as exc:
                with self.tx() as c:
                    status=c.execute('SELECT status FROM requests WHERE key=?',(key,)).fetchone()[0]
                    if status=='sending':c.execute("UPDATE requests SET status='uncertain' WHERE key=?",(key,))
                    c.execute('INSERT OR REPLACE INTO phases VALUES(?,?)',(key,'uncertain' if status=='sending' else 'confirmed_pre_send'))
                return dict(key=key,state='uncertain' if status=='sending' else 'pre_send_stopped',error_type=type(exc).__name__)
            finally:slot.release()
        with ThreadPoolExecutor(max_workers=limit) as pool:results=list(pool.map(send,rows))
        if any(r['state']!='completed' for r in results) and not retain_owner_on_failure:
            with self.tx() as c:c.execute("UPDATE jobs SET status='pending_reconciliation',owner=NULL WHERE id=?",(job,))
        return results
    def reconcile_durable(self,root):
        count=0
        for p in Path(root).glob('*.durable.json'):
            if hashlib.sha256(p.read_bytes()).hexdigest()!=p.with_suffix('.sha256').read_text(encoding='ascii'):raise ValueError('durable receipt hash mismatch')
            d=json.loads(p.read_text(encoding='utf8'));c=self.connect();row=c.execute('SELECT job,status,body FROM requests WHERE key=?',(d['key'],)).fetchone();c.close()
            if not row or row['job']!=d['job'] or hashlib.sha256(row['body'].encode()).hexdigest()!=d['key']:raise ValueError('foreign durable receipt')
            if row['status']!='completed':self.receipt(d['key'],d['actual'],d['raw']);count+=1
        return count
    def snapshot(self):
        state=super().snapshot();state['governance']=self.policy()
        state['simulation_only']=state['governance']['mode']=='simulation'
        c=self.connect()
        try:
            state['timings']=[dict(r) for r in c.execute('SELECT stage,count(*) samples,sum(seconds) total_seconds FROM metrics GROUP BY stage')]
            for job in state['jobs']:
                if c.execute("SELECT 1 FROM sqlite_master WHERE name='budget_pauses'").fetchone():
                    pause=c.execute('SELECT * FROM budget_pauses WHERE job=?',(job['id'],)).fetchone()
                    if pause:job['budget_pause']=dict(pause)
                prior=c.execute('SELECT coalesce(sum(spent),0),coalesce(sum(held),0) FROM legacy_commitments WHERE job=?',(job['id'],)).fetchone() if c.execute("SELECT 1 FROM sqlite_master WHERE name='legacy_commitments'").fetchone() else (0,0)
                job.update(historical_spent=prior[0],historical_reserved=prior[1])
            if c.execute("SELECT 1 FROM sqlite_master WHERE name='response_quality'").fetchone():
                for job in state['jobs']:
                    q=c.execute('SELECT count(*),coalesce(sum(definitive),0),coalesce(sum(blocked),0) FROM response_quality WHERE job=?',(job['id'],)).fetchone()
                    job.update(quality_rows=q[0],definitive_responses=q[1],blocked_indicators=q[2])
                    job['display_status']='complete_requires_review' if job['status']=='complete' and (q[0]<job['responses_saved'] or q[1]<job['responses_saved']) else job['status']
        finally:c.close()
        return state
