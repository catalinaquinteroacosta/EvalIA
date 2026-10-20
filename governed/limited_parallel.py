"""OFFLINE ONLY: bounded independent reads using the existing atomic ledger.

No API transport, credentials, production mounting or automatic uncertain retry.
Each batch waits for every reserved member; uncertainty stops its job only.
"""
from queue_lab import Lab
import json
from concurrent.futures import ThreadPoolExecutor

class ParallelLab(Lab):
    def reserve_batch(self,job,owner,keys,limit=2,*,allow_independent_uncertain=False):
        if type(limit)is not int or not 1<=limit<=5:raise ValueError('limit 1..5')
        if not keys or len(keys)>limit or len(keys)!=len(set(keys)):raise ValueError('invalid batch')
        with self.tx() as c:
            j=c.execute('SELECT * FROM jobs WHERE id=?',(job,)).fetchone()
            if not j or j['status']!='running' or j['owner']!=owner:raise ValueError('wrong owner/state')
            if c.execute('SELECT blocked FROM safety').fetchone()[0]:raise ValueError('global safety stop')
            pending_states="('reserved','sending')" if allow_independent_uncertain else "('reserved','sending','uncertain')"
            if c.execute('SELECT 1 FROM requests WHERE job=? AND status IN '+pending_states,(job,)).fetchone():raise ValueError('pending batch cannot be repeated')
            rows=[]
            for key in keys:
                r=c.execute("SELECT * FROM requests WHERE key=? AND job=? AND status='ready'",(key,job)).fetchone()
                if not r:raise ValueError('foreign, duplicate or unavailable key')
                rows.append(dict(r))
            def committed(where='',args=()):
                value=c.execute("SELECT coalesce(sum(actual+CASE WHEN status IN ('reserved','sending','uncertain') THEN reserve ELSE 0 END),0) FROM requests "+where,args).fetchone()[0]
                if c.execute("SELECT 1 FROM sqlite_master WHERE name='legacy_commitments'").fetchone():
                    value+=c.execute('SELECT coalesce(sum(spent+held),0) FROM legacy_commitments '+where,args).fetchone()[0]
                return value
            global_available=c.execute('SELECT cap FROM settings').fetchone()[0]-committed()
            individual_available=j['cap']-committed('WHERE job=?',(job,))
            selected=[];total=0
            from monetary_policy import monitoring
            monitor_only=monitoring(c)
            for row in rows:
                if not monitor_only and total+row['reserve']>min(global_available,individual_available):break
                selected.append(row);total+=row['reserve']
            if not selected:
                c.execute('CREATE TABLE IF NOT EXISTS budget_pauses(job TEXT PRIMARY KEY,reason TEXT,requested INTEGER,global_available INTEGER,individual_available INTEGER,at REAL)')
                reason='global' if rows[0]['reserve']>global_available else 'individual'
                if rows[0]['reserve']>global_available and rows[0]['reserve']>individual_available:reason='global_and_individual'
                import time
                c.execute('INSERT OR REPLACE INTO budget_pauses VALUES(?,?,?,?,?,?)',(job,reason,rows[0]['reserve'],global_available,individual_available,time.time()))
                c.execute("UPDATE jobs SET status='budget_stopped',owner=NULL WHERE id=?",(job,));return []
            rows=selected
            for r in rows:c.execute("UPDATE requests SET status='reserved' WHERE key=?",(r['key'],))
            return rows

    def execute_simulated_batch(self,job,owner,keys,transport,limit=2):
        if getattr(transport,'simulation_only',False) is not True:raise ValueError('only explicit simulation transport allowed')
        rows=self.reserve_batch(job,owner,keys,limit)
        if not rows:return []
        # Persist all intents before dispatch. Any crash remains conservatively uncertain.
        for row in rows:self.mark_sending(row['key'],owner)
        def send(row):
            try:
                actual,raw=transport(json.loads(row['body']))
                self.receipt(row['key'],actual,raw)
                return {'key':row['key'],'state':'completed'}
            except Exception as exc:
                with self.tx() as c:c.execute("UPDATE requests SET status='uncertain' WHERE key=? AND status='sending'",(row['key'],))
                return {'key':row['key'],'state':'uncertain','error_type':type(exc).__name__}
        with ThreadPoolExecutor(max_workers=limit) as pool:results=list(pool.map(send,rows))
        # Wait for the whole batch: no background sibling request is abandoned.
        if any(r['state']=='uncertain' for r in results):
            with self.tx() as c:c.execute("UPDATE jobs SET status='pending_reconciliation',owner=NULL WHERE id=?",(job,))
        return results

def classify_failure(*,durable_intent,confirmed_no_send=False,receipt_verified=False,http_status=None):
    if receipt_verified:return 'completed_replay_only'
    if confirmed_no_send and not durable_intent:return 'confirmed_pre_send'
    if durable_intent:return 'uncertain_no_retry'
    return 'not_sent_requires_inspection'
