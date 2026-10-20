"""Durable authorization barrier for migrated uncertain attempts. No HTTP.

The source attempt and its commitment are never updated by a substitution.
An ordinary experiment grant is insufficient to replace an uncertain attempt.
"""
import hashlib,json

class ReplacementApprovalRequired(RuntimeError):pass

def initialize(lab):
    with lab.tx() as c:
        c.execute('CREATE TABLE IF NOT EXISTS historical_attempts(job TEXT,key TEXT,attempt TEXT,source_sha256 TEXT,reserve INTEGER,PRIMARY KEY(job,key,attempt))')
        c.execute('CREATE TABLE IF NOT EXISTS replacement_decisions(job TEXT,key TEXT,identity TEXT UNIQUE,grant_json TEXT,PRIMARY KEY(job,key))')

def register(lab,job,key,attempt,source_sha256,reserve):
    initialize(lab)
    with lab.tx() as c:
        previous=c.execute('SELECT source_sha256,reserve FROM historical_attempts WHERE job=? AND key=? AND attempt=?',(job,key,attempt)).fetchone()
        if previous and tuple(previous)!=(source_sha256,reserve):raise ValueError('historical attempt changed')
        c.execute('INSERT OR IGNORE INTO historical_attempts VALUES(?,?,?,?,?)',(job,key,attempt,source_sha256,reserve))

def authorize(lab,job,key,grant):
    initialize(lab)
    with lab.tx() as c:
        rows=c.execute('SELECT attempt,source_sha256,reserve FROM historical_attempts WHERE job=? AND key=? ORDER BY attempt',(job,key)).fetchall()
        request=c.execute('SELECT status,reserve FROM requests WHERE job=? AND key=?',(job,key)).fetchone()
        expected=hashlib.sha256(json.dumps([tuple(r) for r in rows]).encode()).hexdigest()
        if not rows or not request or request['status']!='ready':raise ValueError('replacement requires unresolved historical request')
        if grant.get('explicit_user_approval') is not True or grant.get('job')!=job or grant.get('key')!=key or grant.get('source_sha256')!=expected or grant.get('max_reserve_units')!=request['reserve'] or grant.get('max_attempts')!=1:raise ValueError('exact separate replacement approval required')
        identity=grant.get('identity')
        if not isinstance(identity,str) or not identity or identity in [r[0] for r in rows]:raise ValueError('new attempt identity required')
        wire=json.dumps(grant,sort_keys=True)
        old=c.execute('SELECT grant_json FROM replacement_decisions WHERE job=? AND key=?',(job,key)).fetchone()
        if old and old[0]!=wire:raise ValueError('replacement cannot be authorized twice')
        c.execute('INSERT OR IGNORE INTO replacement_decisions VALUES(?,?,?,?)',(job,key,identity,wire))

def check(lab,job,key):
    c=lab.connect()
    try:
        if not c.execute("SELECT 1 FROM sqlite_master WHERE name='historical_attempts'").fetchone():return None
        old=c.execute('SELECT 1 FROM historical_attempts WHERE job=? AND key=?',(job,key)).fetchone()
        if not old:return None
        state=c.execute('SELECT status FROM requests WHERE job=? AND key=?',(job,key)).fetchone()
        if state and state[0]=='completed':return None
        grant=c.execute('SELECT identity FROM replacement_decisions WHERE job=? AND key=?',(job,key)).fetchone()
        if not grant:raise ReplacementApprovalRequired('historical uncertainty requires separate scoped approval')
        return grant[0]
    finally:c.close()
