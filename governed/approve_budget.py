"""Future explicit budget amendment + continuation. No credential/API access."""
import json,os
from pathlib import Path
from governed_parallel import GovernedLab
from continuity import amend_budget,resume_after_approval
def apply(config_path,decision,job):
    path=Path(config_path);config=json.loads(path.read_text(encoding='utf8'));lab=GovernedLab(config['coordinator'])
    if decision.get('resume_job')!=job:raise ValueError('explicit continuation scope required')
    amend_budget(lab,decision)
    # Requeue only after the audited amendment. Restart/launch is separate.
    resume_after_approval(lab,job,explicit_resume=True)
    config['explicit_real_activation']=True
    if decision['scope']=='global':config['approved_global_cap_usd']=decision['new_usd']
    temporary=path.with_suffix('.budget-approved.tmp')
    with temporary.open('x',encoding='utf8') as f:json.dump(config,f,indent=2);f.flush();os.fsync(f.fileno())
    os.replace(temporary,path)
    return dict(approved=True,job=job,paid_calls=0,workers_started=False)
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--decision',required=True);p.add_argument('--job',required=True);a=p.parse_args()
    print(json.dumps(apply(a.config,json.loads(Path(a.decision).read_text(encoding='utf8')),a.job)))
