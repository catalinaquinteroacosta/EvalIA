"""Route future unresolved cases to Luna within the experiment's authorized budget."""
import json,subprocess,time,sys
from pathlib import Path
from direct_recovery import prepare,connect,wire,digest,consolidated
from queue_lab import units
from governed_parallel import GovernedLab

def start(config,experiment):
 if experiment==72:return
 root=Path(config['project_root'])/'.evalia-private/direct_recovery';folder=root/str(experiment)
 if (folder/'authorization.json').exists():return
 cid,m=prepare(config,experiment,root/'recovery.db',folder)
 with connect(root/'recovery.db')as c:done={r['id']for r in c.execute('select id from decisions where campaign=?',(cid,))}
 final_manual={(r['response_id'],r['code'])for r in consolidated(config,experiment,root/'recovery.db')['rows']if r.get('manual_evaluator')}
 manual_ids={r['id']for r in m['cases']if(r['response_id'],r['code'])in final_manual}
 rows=[r for r in m['requests']if r['id']not in done and r['id']not in manual_ids]
 if not rows:return
 lab=GovernedLab(config['coordinator']);estimate=sum(units(r['reserved_usd'])for r in rows)
 with lab.tx()as c:
  j=c.execute('select *from jobs where experiment=?',(experiment,)).fetchone()
  if not j or j['owner'] is not None:return
  def committed(where='',args=()):return c.execute("select coalesce(sum(actual+case when status in ('reserved','sending','uncertain')then reserve else 0 end),0)from requests "+where,args).fetchone()[0]+c.execute('select coalesce(sum(spent+held),0)from legacy_commitments '+where,args).fetchone()[0]
  globalcap=c.execute('select cap from settings').fetchone()[0]
  from monetary_policy import monitoring
  if not monitoring(c) and (committed('where job=?',(j['id'],))+estimate>j['cap'] or committed()+estimate>globalcap):
   # The experiment remains exportable and available for manual completion.
   (folder/'automatic_recovery_status.json').write_text(wire(dict(state='manual_available',reason='authorized_budget_insufficient',estimate_usd=estimate/1e9)),encoding='utf8');return
  auth=dict(explicit_user_approval=True,approval_basis='User requested automatic Luna fallback for future evaluations',manifest_sha256=cid,allowed_ids=[r['id']for r in rows],max_calls=len(rows),job=j['id'],at=time.time(),no_uncertain_retries=True,individual_cap_usd=str(j['cap']/1e9),global_cap_usd=str(globalcap/1e9))
  position=(c.execute('select max(position)from requests where job=?',(j['id'],)).fetchone()[0]or 0)+1
  for i,r in enumerate(rows):c.execute('insert into requests(key,job,position,body,reserve,status)values(?,?,?,?,?,?)',(digest(r['body']),j['id'],position+i,wire(r['body']),units(r['reserved_usd']),'ready'))
 (folder/'authorization.json').write_text(wire(auth),encoding='utf8');(folder/'config.json').write_text(wire(config),encoding='utf8')
 with (folder/'worker.log').open('ab')as log:subprocess.Popen([config['python'],'-X','utf8','-B',str(Path(__file__).with_name('direct_recovery_worker.py')),'--config',str(folder/'config.json'),'--campaign',cid,'--database',str(root/'recovery.db'),'--folder',str(folder)],cwd=config['project_root'],stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
