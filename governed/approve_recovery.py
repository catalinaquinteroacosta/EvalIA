"""Explicit future economic operation; never called by installation or GET.
Only stores scoped approvals. Does not load credentials or dispatch requests.
"""
import json,hashlib,os
from pathlib import Path
from governed_parallel import GovernedLab
from historical_recovery_gate import authorize
def approve(config_path,decision):
    path=Path(config_path);config=json.loads(path.read_text(encoding='utf8'));lab=GovernedLab(config['coordinator']);job=decision['job']
    if decision.get('explicit_user_approval') is not True or decision.get('continue_original_requests') is not True:raise ValueError('new explicit economic approval required')
    c=lab.connect()
    try:
        row=c.execute('SELECT experiment,cap,status FROM jobs WHERE id=?',(job,)).fetchone()
        scope=[tuple(r) for r in c.execute('SELECT position,key FROM requests WHERE job=? ORDER BY position',(job,))]
    finally:c.close()
    from queue_lab import units
    if not row or row['experiment']==72 or units(decision['max_usd'])!=row['cap'] or row['status']!='awaiting_authorization':raise ValueError('wrong scope, state or changed cap')
    for grant in decision.get('replacements',[]):authorize(lab,job,grant['key'],grant)
    lab.authorize_real_job(job,dict(job=job,experiment=row['experiment'],max_usd=decision['max_usd'],scope='exact sealed manifest only',explicit_user_approval=True,body_scope_sha256=hashlib.sha256(json.dumps(scope).encode()).hexdigest()))
    config['explicit_real_activation']=True
    # Job may become queued before this atomic switch, but cannot load a key while false.
    temporary=path.with_suffix('.approved.tmp')
    with temporary.open('x',encoding='utf8') as f:json.dump(config,f,indent=2);f.flush();os.fsync(f.fileno())
    os.replace(temporary,path)
    return dict(job=job,approved=True,requests_transmitted=0,worker_started=False)
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--decision',required=True);a=p.parse_args()
    print(json.dumps(approve(a.config,json.loads(Path(a.decision).read_text(encoding='utf8')))))
