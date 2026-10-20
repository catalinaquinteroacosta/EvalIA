"""New campaign permission only; balances and historical grants are not approvals."""
import json,hashlib
from decimal import Decimal
from queue_lab import units
def validate_approval(lab,m,approval):
    from .engine import digest
    if approval.get('explicit_user_approval')is not True or approval.get('scope')!='double-resolution-exact-campaign' or approval.get('manifest_sha256')!=digest(m) or not approval.get('authorization_id'):raise ValueError('new exact campaign approval required')
    if approval.get('max_calls')!=len(m['requests']) or approval.get('max_semantic_stages_per_case')!=2:raise ValueError('call limit differs')
    if approval.get('kind')not in('pilot','qualified_campaign'):raise ValueError('approval type')
    if approval['kind']=='qualified_campaign' and not approval.get('independent_quality_report_sha256'):raise ValueError('independent quality qualification required')
    cap=units(approval['max_usd'])
    if cap<=0:raise ValueError('positive explicit campaign cap required')
    con=lab.connect()
    try:
        row=con.execute('SELECT cap,experiment FROM jobs WHERE id=?',(m['job'],)).fetchone()
        if not row or row[1]!=m['cases'][0]['experiment']:raise ValueError('parent scope differs')
        def spent(where='',args=()):
            x=con.execute("SELECT coalesce(sum(actual+CASE WHEN status IN ('sending','reserved','uncertain') THEN reserve ELSE 0 END),0) FROM requests "+where,args).fetchone()[0]
            if con.execute("SELECT 1 FROM sqlite_master WHERE name='legacy_commitments'").fetchone():x+=con.execute('SELECT coalesce(sum(spent+held),0) FROM legacy_commitments '+where,args).fetchone()[0]
            return x
        globalcap=con.execute('SELECT cap FROM settings').fetchone()[0]
        if row[0]!=units(m['cap']) or cap>row[0]-spent('WHERE job=?',(m['job'],)) or cap>globalcap-spent():raise ValueError('campaign cap exceeds retained individual/global commitments')
    finally:con.close()
    return cap
def register(lab,m,approval):
    text=json.dumps(approval,sort_keys=True);h=hashlib.sha256(text.encode()).hexdigest()
    with lab.tx()as con:
        con.execute('CREATE TABLE IF NOT EXISTS adjudication_approvals(job TEXT PRIMARY KEY,payload TEXT,sha256 TEXT)')
        old=con.execute('SELECT sha256 FROM adjudication_approvals WHERE job=?',(m['job'],)).fetchone()
        if old:
            if old[0]!=h:raise ValueError('approval immutable')
            return h
    validate_approval(lab,m,approval)
    with lab.tx()as con:
        con.execute('CREATE TABLE IF NOT EXISTS adjudication_approvals(job TEXT PRIMARY KEY,payload TEXT,sha256 TEXT)')
        old=con.execute('SELECT sha256 FROM adjudication_approvals WHERE job=?',(m['job'],)).fetchone()
        if old and old[0]!=h:raise ValueError('approval immutable')
        con.execute('INSERT OR IGNORE INTO adjudication_approvals VALUES(?,?,?)',(m['job'],text,h))
    return h
def active(lab,m):
    from .engine import digest
    con=lab.connect()
    try:
        if not con.execute("SELECT 1 FROM sqlite_master WHERE name='adjudication_approvals'").fetchone():raise ValueError('no campaign activation')
        row=con.execute('SELECT payload,sha256 FROM adjudication_approvals WHERE job=?',(m['job'],)).fetchone()
        if not row or hashlib.sha256(row[0].encode()).hexdigest()!=row[1]:raise ValueError('missing/corrupt campaign approval')
        grant=json.loads(row[0])
        if grant['manifest_sha256']!=digest(m):raise ValueError('foreign campaign approval')
        return grant
    finally:con.close()
def budget_prefix(lab,m,keys,approval):
    scope={__import__('hashlib').sha256(json.dumps(r['body'],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest() for r in m['requests']}
    if not set(keys)<=scope:raise ValueError('body outside campaign grant')
    con=lab.connect()
    try:
        rows=[dict(r) for r in con.execute('SELECT * FROM requests WHERE job=?',(m['job'],)) if r['key']in scope]
        consumed=sum(r['actual']+(r['reserve'] if r['status']in('reserved','sending','uncertain')else 0) for r in rows)
        allowed=[];available=units(approval['max_usd'])-consumed;bykey={r['key']:r for r in rows}
        for key in keys:
            if bykey[key]['reserve']>available:break
            allowed.append(key);available-=bykey[key]['reserve']
        return allowed
    finally:con.close()
