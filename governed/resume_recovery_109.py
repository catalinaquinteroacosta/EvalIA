"""Reconcile proven unsent local failures, preserve evidence, resume authorized scope."""
import sys,json,subprocess,time
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root),str(root/'governed'),str(root/'venv/Lib/site-packages')]
from direct_recovery import digest
from governed_parallel import GovernedLab
from backend.reconcile_no_send import reconcile
cfg=json.loads((root/'.evalia-private/governed_joint_install_20261017/config.json').read_text())
folder=root/'.evalia-private/direct_recovery/109';auth=json.loads((folder/'authorization.json').read_text());manifest=json.loads((folder/'manifest.json').read_text())
lab=GovernedLab(cfg['coordinator']);job=auth['job'];count=0
with lab.connect()as c:assert c.execute('select owner from jobs where id=?',(job,)).fetchone()[0] is None
for row in manifest['requests']:
 key=digest(row['body']);native=folder/'native'/row['id']
 with lab.connect()as c:state=c.execute('select status from requests where key=?',(key,)).fetchone()[0]
 if state=='uncertain':
  # Full native transport proof, not merely an exception name, is required.
  reconcile(native)
  archive=folder/'confirmed_no_send_archive'/row['id'];archive.parent.mkdir(exist_ok=True)
  assert native.resolve().is_relative_to(folder.resolve()) and archive.resolve().is_relative_to(folder.resolve())
  native.rename(archive)
  with lab.tx()as c:
   c.execute('CREATE TABLE IF NOT EXISTS no_send_reconciliations(key TEXT PRIMARY KEY,evidence TEXT,created REAL)')
   c.execute('insert into no_send_reconciliations values(?,?,?)',(key,str(archive),time.time()))
   c.execute("update requests set status='ready' where key=? and status='uncertain'",(key,))
   c.execute("update phases set phase='confirmed_pre_send' where key=?",(key,))
  count+=1
 elif state=='reserved':
  assert not native.exists() or not list(native.glob('*.intent.json'))
  with lab.tx()as c:c.execute("update requests set status='ready' where key=? and status='reserved'",(key,))
with lab.tx()as c:c.execute('update safety set blocked=0')
with (folder/'worker.log').open('ab')as log:
 p=subprocess.Popen([cfg['python'],'-X','utf8','-B',str(root/'governed/direct_recovery_worker.py'),'--config',str(folder/'config.json'),'--campaign',auth['manifest_sha256'],'--database',str(root/'.evalia-private/direct_recovery/recovery.db'),'--folder',str(folder)],cwd=root,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
print(json.dumps(dict(reconciled_confirmed_unsent=count,worker_pid=p.pid,scope=577,historical_uncertain_retried=False)))
