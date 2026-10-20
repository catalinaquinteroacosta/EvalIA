"""Isolated SIMULATION ONLY. No API, credentials, backend imports or active DB."""
import sqlite3,json,hashlib,html
from contextlib import contextmanager
from decimal import Decimal

def units(value):
    n=Decimal(str(value))*10**9
    if not n.is_finite() or n<0 or n!=n.to_integral_value():raise ValueError('invalid money')
    return int(n)

class Lab:
    def __init__(self,path):self.path=str(path)
    def connect(self):
        c=sqlite3.connect(self.path,timeout=15);c.row_factory=sqlite3.Row
        c.execute('PRAGMA foreign_keys=ON');return c
    @contextmanager
    def tx(self):
        c=self.connect()
        try:c.execute('BEGIN IMMEDIATE');yield c;c.commit()
        except Exception:c.rollback();raise
        finally:c.close()
    def initialize(self,cap,workers=1):
        if workers not in range(1,6):raise ValueError('workers must be 1..5')
        c=self.connect();c.execute('PRAGMA journal_mode=WAL')
        c.executescript('''CREATE TABLE IF NOT EXISTS settings(id INTEGER PRIMARY KEY CHECK(id=1),cap INTEGER,workers INTEGER);
        CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,experiment INTEGER UNIQUE,cap INTEGER,status TEXT,owner TEXT);
        CREATE TABLE IF NOT EXISTS safety(id INTEGER PRIMARY KEY CHECK(id=1),blocked INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS results(job TEXT REFERENCES jobs(id),response TEXT,payload TEXT,payload_hash TEXT,PRIMARY KEY(job,response));
        CREATE TABLE IF NOT EXISTS response_contracts(job TEXT REFERENCES jobs(id),response TEXT,keys_json TEXT,PRIMARY KEY(job,response));
        CREATE TABLE IF NOT EXISTS requests(key TEXT PRIMARY KEY,job TEXT REFERENCES jobs(id),position INTEGER,body TEXT,reserve INTEGER,actual INTEGER DEFAULT 0,status TEXT,receipt TEXT,receipt_hash TEXT,UNIQUE(job,position));''')
        if c.execute('SELECT 1 FROM settings').fetchone():c.close();raise ValueError('cannot reset existing accounting')
        c.execute('INSERT INTO settings VALUES(1,?,?)',(units(cap),workers));c.execute('INSERT INTO safety VALUES(1,0)');c.commit();c.close()
    def configure_workers(self,n):
        if type(n)is not int or n not in range(1,6):raise ValueError('workers must be 1..5')
        with self.tx() as c:
            if c.execute("SELECT count(*) FROM jobs WHERE status='running'").fetchone()[0]>n:raise ValueError('wait for active workers')
            c.execute('UPDATE settings SET workers=?',(n,))
    def enqueue_simulation(self,job,experiment,cap,bodies,*,initial_status='queued'):
        if initial_status not in ('queued','awaiting_authorization'):raise ValueError('invalid initial status')
        if experiment==72:raise ValueError('protected experiment')
        if not bodies or units(cap)<=0:raise ValueError('positive cap and nonempty request list required')
        with self.tx() as c:
            c.execute('INSERT INTO jobs VALUES(?,?,?, ?,NULL)',(job,experiment,units(cap),initial_status))
            contracts={}
            for i,row in enumerate(bodies):
                body=json.dumps(row['body'],sort_keys=True,ensure_ascii=False,separators=(',',':'))
                key=hashlib.sha256(body.encode()).hexdigest()
                c.execute('INSERT INTO requests(key,job,position,body,reserve,status) VALUES(?,?,?,?,?,?)',(key,job,i,body,units(row['reserve']),'ready'))
                if 'response' in row:contracts.setdefault(str(row['response']),[]).append(key)
            for response,keys in contracts.items():c.execute('INSERT INTO response_contracts VALUES(?,?,?)',(job,response,json.dumps(sorted(keys))))
    def claim(self,owner):
        with self.tx() as c:
            if c.execute('SELECT blocked FROM safety').fetchone()[0]:return None
            if c.execute("SELECT 1 FROM jobs WHERE owner=? AND status='running'",(owner,)).fetchone():return None
            if c.execute("SELECT count(*) FROM jobs WHERE status='running'").fetchone()[0]>=c.execute('SELECT workers FROM settings').fetchone()[0]:return None
            row=c.execute("SELECT id FROM jobs WHERE status='queued' ORDER BY rowid LIMIT 1").fetchone()
            if not row:return None
            c.execute("UPDATE jobs SET status='running',owner=? WHERE id=?",(owner,row['id']));return row['id']
    def reserve_next(self,job,owner,key=None):
        with self.tx() as c:
            j=c.execute('SELECT * FROM jobs WHERE id=?',(job,)).fetchone()
            if j['status']=='complete':return None
            if j['owner']!=owner or j['status']!='running':raise ValueError('wrong owner/state')
            if c.execute('SELECT blocked FROM safety').fetchone()[0]:raise ValueError('global safety stop')
            if c.execute("SELECT 1 FROM requests WHERE job=? AND status IN ('reserved','sending','uncertain')",(job,)).fetchone():raise ValueError('pending request cannot be resent')
            row=c.execute("SELECT * FROM requests WHERE job=? AND status='ready' AND (? IS NULL OR key=?) ORDER BY position LIMIT 1",(job,key,key)).fetchone()
            if key is not None and not row:raise ValueError('requested body is not ready in job')
            if not row:
                missing=c.execute('SELECT count(*) FROM response_contracts r WHERE job=? AND NOT EXISTS(SELECT 1 FROM results s WHERE s.job=r.job AND s.response=r.response)',(job,)).fetchone()[0]
                c.execute('UPDATE jobs SET status=?,owner=NULL WHERE id=?',('transport_complete' if missing else 'complete',job));return None
            def committed(where='',args=()):return c.execute("SELECT coalesce(sum(actual + CASE WHEN status IN ('reserved','sending','uncertain') THEN reserve ELSE 0 END),0) FROM requests "+where,args).fetchone()[0]
            global_cap=c.execute('SELECT cap FROM settings').fetchone()[0]
            from monetary_policy import monitoring
            if not monitoring(c) and (committed()+row['reserve']>global_cap or committed('WHERE job=?',(job,))+row['reserve']>j['cap']):
                c.execute("UPDATE jobs SET status='budget_stopped',owner=NULL WHERE id=?",(job,));return None
            c.execute("UPDATE requests SET status='reserved' WHERE key=?",(row['key'],));return dict(row)
    def mark_sending(self,key,owner):
        with self.tx() as c:
            if c.execute('SELECT blocked FROM safety').fetchone()[0]:raise ValueError('global safety stop')
            row=c.execute('SELECT r.status,j.owner FROM requests r JOIN jobs j ON r.job=j.id WHERE key=?',(key,)).fetchone()
            if row['status']!='reserved' or row['owner']!=owner:raise ValueError('not reserved by worker')
            c.execute("UPDATE requests SET status='sending' WHERE key=?",(key,))
    def receipt(self,key,actual,raw):
        value=units(actual);wire=json.dumps(raw,sort_keys=True);digest=hashlib.sha256(wire.encode()).hexdigest()
        with self.tx() as c:
            row=c.execute('SELECT * FROM requests WHERE key=?',(key,)).fetchone()
            if row['status']=='completed':
                if row['receipt_hash']!=digest or row['actual']!=value:raise ValueError('receipt mismatch')
                return
            if row['status'] not in ('sending','uncertain'):raise ValueError('no transmission intent')
            c.execute("UPDATE requests SET status='completed',actual=?,receipt=?,receipt_hash=? WHERE key=?",(value,wire,digest,key))
            from monetary_policy import monitoring
            if value>row['reserve'] and not monitoring(c):
                c.execute("UPDATE jobs SET status='review_required',owner=NULL WHERE id=?",(row['job'],))
                c.execute('UPDATE safety SET blocked=1')
    def recover_after_workers_stopped(self,*,workers_stopped=False):
        # Explicit maintenance only after old workers have terminated; never timeout-based resend.
        if workers_stopped is not True:raise ValueError('explicit stopped-worker confirmation required')
        with self.tx() as c:
            c.execute("UPDATE requests SET status='uncertain' WHERE status='sending'")
            c.execute("UPDATE requests SET status='ready' WHERE status='reserved'")
            c.execute("UPDATE jobs SET owner=NULL,status=CASE WHEN EXISTS(SELECT 1 FROM requests r WHERE r.job=jobs.id AND r.status='uncertain') THEN 'pending_reconciliation' ELSE 'queued' END WHERE status='running'")
    def persist_result(self,job,response,keys,payload):
        wire=json.dumps(payload,sort_keys=True,ensure_ascii=False);digest=hashlib.sha256(wire.encode()).hexdigest()
        if not keys or len(keys)!=len(set(keys)):raise ValueError('exact request set required')
        with self.tx() as c:
            contract=c.execute('SELECT keys_json FROM response_contracts WHERE job=? AND response=?',(job,str(response))).fetchone()
            if not contract or json.loads(contract['keys_json'])!=sorted(keys):raise ValueError('response request scope incomplete or changed')
            experiment=c.execute('SELECT experiment FROM jobs WHERE id=?',(job,)).fetchone()[0]
            if payload.get('experiment')!=experiment:raise ValueError('result experiment identity differs')
            for key in keys:
                r=c.execute('SELECT job,status,body FROM requests WHERE key=?',(key,)).fetchone()
                if not r or r['job']!=job or r['status']!='completed':raise ValueError('response has incomplete or foreign readers')
                body=json.loads(r['body'])
                for field in ('model','turn') if body.get('synthetic') else ():
                    if field in body and payload.get(field)!=body[field]:raise ValueError('result model/turn identity differs')
            old=c.execute('SELECT payload_hash FROM results WHERE job=? AND response=?',(job,response)).fetchone()
            if old:
                if old['payload_hash']!=digest:raise ValueError('cannot overwrite result')
                return
            c.execute('INSERT INTO results VALUES(?,?,?,?)',(job,response,wire,digest))
            missing=c.execute('SELECT count(*) FROM response_contracts r WHERE job=? AND NOT EXISTS(SELECT 1 FROM results s WHERE s.job=r.job AND s.response=r.response)',(job,)).fetchone()[0]
            pending=c.execute("SELECT count(*) FROM requests WHERE job=? AND status!='completed'",(job,)).fetchone()[0]
            if not missing and not pending:c.execute("UPDATE jobs SET status='complete',owner=NULL WHERE id=?",(job,))
    def resume_reconciled(self,job):
        with self.tx() as c:
            row=c.execute('SELECT status,owner FROM jobs WHERE id=?',(job,)).fetchone()
            if row['status']!='pending_reconciliation' or row['owner'] is not None:raise ValueError('explicit reconciled job required')
            if c.execute("SELECT 1 FROM requests WHERE job=? AND status IN ('reserved','sending','uncertain')",(job,)).fetchone():raise ValueError('unreconciled request remains')
            if c.execute('SELECT blocked FROM safety').fetchone()[0]:raise ValueError('global safety stop')
            c.execute("UPDATE jobs SET status='queued' WHERE id=?",(job,))
    def load_result(self,job,response):
        c=self.connect()
        try:
            row=c.execute('SELECT payload,payload_hash FROM results WHERE job=? AND response=?',(job,response)).fetchone()
            if not row:return None
            if hashlib.sha256(row['payload'].encode()).hexdigest()!=row['payload_hash']:raise ValueError('result corrupted')
            return json.loads(row['payload'])
        finally:c.close()
    def snapshot(self):
        c=self.connect()
        try:
            jobs=[dict(r) for r in c.execute("SELECT j.*,count(r.key) total,sum(r.status='completed') completed,sum(r.actual) spent,coalesce(sum(CASE WHEN r.status IN ('reserved','sending','uncertain') THEN r.reserve ELSE 0 END),0) pending FROM jobs j LEFT JOIN requests r ON r.job=j.id GROUP BY j.id")]
            for job in jobs:job['responses_saved']=c.execute('SELECT count(*) FROM results WHERE job=?',(job['id'],)).fetchone()[0]
            return {'simulation_only':True,'workers':c.execute('SELECT workers FROM settings').fetchone()[0],'global_blocked':bool(c.execute('SELECT blocked FROM safety').fetchone()[0]),'jobs':jobs}
        finally:c.close()
    def panel(self):
        rows=''.join('<tr>'+''.join('<td>'+html.escape(str(j[k]))+'</td>' for k in ('experiment','status','completed','total','spent','pending'))+'</tr>' for j in self.snapshot()['jobs'])
        return '<!doctype html><meta charset="utf-8"><h1>Laboratorio aislado — SOLO SIMULACIÓN</h1><p>Importes en milmillonésimas de dólar. Sin API real ni resultados clínicos.</p><table><tr><th>Experimento</th><th>Estado</th><th>Completadas</th><th>Total</th><th>Gasto simulado</th><th>Reserva pendiente</th></tr>'+rows+'</table>'
