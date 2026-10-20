"""Import explicitly selected TOP-LEVEL journals from a quiescent backup only.
No scan of production, no credentials, no reset or release of uncertainty.
"""
import json,hashlib
from pathlib import Path
from queue_lab import units

def import_journals(lab,backup_root,sources,*,quiescent_verified=False):
    if quiescent_verified is not True:raise ValueError('quiescent backup required')
    root=Path(backup_root).resolve();rows=[];runs=set()
    for source in sources:
        path=(root/source['relative_path']).resolve()
        if not path.is_relative_to(root) or source.get('top_level') is not True:raise ValueError('explicit top-level source required')
        raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
        if digest!=source['sha256']:raise ValueError('journal changed')
        d=json.loads(raw);spent=units(d['genesis']['prior_spent_usd']);held=0
        for run,e in d['entries'].items():
            if run in runs:raise ValueError('same run in two top-level journals; reconcile before migration')
            runs.add(run)
            if e['status']=='settled':spent+=units(e['actual_usd'])
            elif e['status'] in ('reserved','uncertain'):held+=units(e['reservation_usd'])
            else:raise ValueError('unknown journal state')
        rows.append((source['source_identity'],digest,source.get('job'),spent,held))
    if len({r[0] for r in rows})!=len(rows):raise ValueError('duplicate journal identity')
    with lab.tx() as c:
        if c.execute("SELECT 1 FROM jobs WHERE status='running'").fetchone():raise ValueError('stop acquisition first')
        c.execute('CREATE TABLE IF NOT EXISTS legacy_commitments(source TEXT PRIMARY KEY,sha256 TEXT,job TEXT,spent INTEGER,held INTEGER)')
        for row in rows:
            previous=c.execute('SELECT sha256,job,spent,held FROM legacy_commitments WHERE source=?',(row[0],)).fetchone()
            if previous and tuple(previous)!=row[1:]:raise ValueError('cannot replace historical accounting')
            c.execute('INSERT OR IGNORE INTO legacy_commitments VALUES(?,?,?,?,?)',row)
        total=c.execute('SELECT coalesce(sum(spent+held),0) FROM legacy_commitments').fetchone()[0]
        total+=c.execute("SELECT coalesce(sum(actual+CASE WHEN status IN ('reserved','sending','uncertain') THEN reserve ELSE 0 END),0) FROM requests").fetchone()[0]
        if total>c.execute('SELECT cap FROM settings').fetchone()[0]:raise ValueError('history exceeds approved global cap')
    return dict(imported_sources=len(rows),retained_commitment_units=total)
