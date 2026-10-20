"""Durable no-POST recovery and explicit budget amendments. Never sends HTTP."""
import json,hashlib,time
from queue_lab import units

def migrate(lab):
    with lab.tx() as c:
        c.execute('CREATE TABLE IF NOT EXISTS retry_policy(id INTEGER PRIMARY KEY,max_attempts INTEGER,base_seconds REAL,max_seconds REAL)')
        c.execute('INSERT OR IGNORE INTO retry_policy VALUES(1,3,2,30)')
        c.execute('CREATE TABLE IF NOT EXISTS retry_schedule(key TEXT PRIMARY KEY,ordinal INTEGER,not_before REAL)')
        c.execute('CREATE TABLE IF NOT EXISTS attempt_history(key TEXT,ordinal INTEGER,folder TEXT,proof_sha256 TEXT,evidence TEXT,admission TEXT,PRIMARY KEY(key,ordinal))')
        c.execute('CREATE TABLE IF NOT EXISTS budget_pauses(job TEXT PRIMARY KEY,reason TEXT,requested INTEGER,global_available INTEGER,individual_available INTEGER,at REAL)')
        c.execute('CREATE TABLE IF NOT EXISTS budget_amendments(id TEXT PRIMARY KEY,scope TEXT,scope_id TEXT,old_cap INTEGER,new_cap INTEGER,authorization TEXT,sha256 TEXT,at REAL)')

def configure_retry(lab,*,max_attempts=3,base_seconds=2,max_seconds=30):
    if type(max_attempts)is not int or not 1<=max_attempts<=10 or not 0<=base_seconds<=max_seconds<=300:raise ValueError('invalid bounded retry policy')
    migrate(lab)
    with lab.tx() as c:
        if c.execute("SELECT 1 FROM jobs WHERE status='running'").fetchone():raise ValueError('configure only while stopped')
        c.execute('UPDATE retry_policy SET max_attempts=?,base_seconds=?,max_seconds=? WHERE id=1',(max_attempts,base_seconds,max_seconds))

def attempt(lab,key):
    c=lab.connect()
    try:
        if not c.execute("SELECT 1 FROM sqlite_master WHERE name='retry_schedule'").fetchone():return 0,0
        row=c.execute('SELECT ordinal,not_before FROM retry_schedule WHERE key=?',(key,)).fetchone()
        return tuple(row) if row else (0,0)
    finally:c.close()

def record_no_send(lab,job,key,proof,*,now=None):
    """Provider validates native auth/body/phases and settles its mirror first.
    Crash between mirror/central settlement is safe: this transition is idempotent.
    """
    if proof.get('classification')!='confirmed_no_api_send' or proof.get('request_body_key')!=key or proof.get('verified_native_proof') is not True:raise ValueError('verified owned no-POST proof required')
    migrate(lab);now=time.time() if now is None else now
    wire=json.dumps(proof,sort_keys=True);sha=hashlib.sha256(wire.encode()).hexdigest()
    with lab.tx() as c:
        previous=c.execute('SELECT proof_sha256 FROM attempt_history WHERE key=? AND ordinal=?',(key,proof['ordinal'])).fetchone()
        if previous:
            if previous[0]!=sha:raise ValueError('attempt proof changed')
            return c.execute('SELECT status FROM requests WHERE key=?',(key,)).fetchone()[0]
        row=c.execute('SELECT job,status,actual FROM requests WHERE key=?',(key,)).fetchone()
        if not row or row['job']!=job or row['status'] not in ('sending','uncertain','confirmed_no_send') or row['actual']!=0:raise ValueError('cannot release completed, foreign or unsupported reservation')
        current=c.execute('SELECT ordinal FROM retry_schedule WHERE key=?',(key,)).fetchone()
        ordinal=current[0] if current else 0
        if ordinal!=proof['ordinal']:raise ValueError('attempt lineage mismatch')
        policy=c.execute('SELECT * FROM retry_policy').fetchone()
        # A one-off historical substitution grant is never expanded by retry policy.
        historical=c.execute("SELECT 1 FROM sqlite_master WHERE name='historical_attempts'").fetchone() and c.execute('SELECT 1 FROM historical_attempts WHERE job=? AND key=?',(job,key)).fetchone()
        retry=not historical and ordinal+1<policy['max_attempts']
        admission=c.execute('SELECT * FROM admissions WHERE key=?',(key,)).fetchone()
        c.execute('INSERT INTO attempt_history VALUES(?,?,?,?,?,?)',(key,ordinal,proof['folder'],sha,wire,json.dumps(dict(admission)) if admission else None))
        c.execute('DELETE FROM admissions WHERE key=?',(key,))
        c.execute("INSERT OR REPLACE INTO phases VALUES(?,'confirmed_pre_send')",(key,))
        c.execute('UPDATE requests SET status=? WHERE key=?',('ready' if retry else 'retry_exhausted',key))
        delay=min(policy['max_seconds'],policy['base_seconds']*2**ordinal)
        c.execute('INSERT OR REPLACE INTO retry_schedule VALUES(?,?,?)',(key,ordinal+1,now+delay))
        return 'ready' if retry else 'retry_exhausted'

def execute(lab,once,job,owner,keys,provider,root,*,token_bound=None,fault=None,retain_owner_on_failure=False):
    migrate(lab);pending=list(keys);results={}
    while pending:
        wait=max(attempt(lab,key)[1] for key in pending)-time.time()
        while wait>0:time.sleep(min(wait,1));wait=max(attempt(lab,key)[1] for key in pending)-time.time()
        batch=once(job,owner,pending,provider,root,token_bound=token_bound,fault=fault,retain_owner_on_failure=True)
        if not batch:return []
        retry=[]
        for result in batch:
            key=result['key'];results[key]=result
            if result['state']=='completed':continue
            proof=provider.reconcile_no_send(key) if callable(getattr(provider,'reconcile_no_send',None)) else None
            if proof:
                state=record_no_send(lab,job,key,proof)
                results[key]={**result,'state':state}
                if state=='ready':retry.append(key)
        # A budget-fitting prefix can be smaller than the originally requested batch.
        attempted={r['key'] for r in batch}
        pending=[k for k in pending if k not in attempted]+retry
    answer=[results[k] for k in keys]
    if any(r['state']!='completed' for r in answer) and not retain_owner_on_failure:
        with lab.tx() as c:c.execute("UPDATE jobs SET status='pending_reconciliation',owner=NULL WHERE id=? AND owner=?",(job,owner))
    return answer

def amend_budget(lab,decision):
    """Stores authority and changes only the explicitly selected cap. No requeue/API."""
    if decision.get('explicit_user_approval') is not True or not decision.get('authorization_id'):raise ValueError('explicit economic authorization required')
    scope=decision.get('scope');scope_id=decision.get('scope_id')
    if scope not in ('global','job') or scope=='global' and scope_id!='global':raise ValueError('explicit budget scope required')
    old,new=units(decision['previous_usd']),units(decision['new_usd'])
    if new<=old:raise ValueError('explicit increase required')
    migrate(lab);wire=json.dumps(decision,sort_keys=True);sha=hashlib.sha256(wire.encode()).hexdigest()
    with lab.tx() as c:
        previous=c.execute('SELECT sha256 FROM budget_amendments WHERE id=?',(decision['authorization_id'],)).fetchone()
        if previous:
            if previous[0]!=sha:raise ValueError('authorization changed')
            return
        if scope=='global':current=c.execute('SELECT cap FROM settings').fetchone()[0]
        else:
            row=c.execute('SELECT cap,experiment FROM jobs WHERE id=?',(scope_id,)).fetchone()
            if not row or row['experiment']==72:raise ValueError('invalid experiment budget')
            current=row['cap']
        if current!=old:raise ValueError('stale prior budget')
        c.execute('INSERT INTO budget_amendments VALUES(?,?,?,?,?,?,?,?)',(decision['authorization_id'],scope,scope_id,old,new,wire,sha,time.time()))
        if scope=='global':c.execute('UPDATE settings SET cap=?',(new,))
        else:c.execute('UPDATE jobs SET cap=? WHERE id=?',(new,scope_id))

def resume_after_approval(lab,job,*,explicit_resume=False):
    if explicit_resume is not True:raise ValueError('explicit continuation required')
    with lab.tx() as c:
        row=c.execute('SELECT status,owner FROM jobs WHERE id=?',(job,)).fetchone()
        if not row or row['owner'] is not None or row['status'] not in ('budget_stopped','pending_reconciliation','paused_authorization','queued'):raise ValueError('job is not safely paused')
        if c.execute("SELECT 1 FROM requests WHERE job=? AND status IN ('reserved','sending')",(job,)).fetchone():raise ValueError('active request remains')
        if c.execute('SELECT blocked FROM safety').fetchone()[0]:raise ValueError('global safety stop')
        if not c.execute('SELECT 1 FROM grants WHERE job=? AND explicit_approval=1',(job,)).fetchone():raise ValueError('original spend grant missing')
        c.execute("UPDATE jobs SET status='queued' WHERE id=?",(job,))
