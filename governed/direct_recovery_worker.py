"""Explicit campaign worker; bounded calls, durable receipts, no uncertain retries."""
import argparse,json,os,sys,time,hashlib
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'governed'),str(ROOT/'venv/Lib/site-packages')]
from direct_recovery import connect,wire,digest,store
from governed_parallel import GovernedLab
from queue_lab import units
from supervision import Fence

def run(config,campaign,db,folder):
 from backend import luna_reader as reader,luna_runner,luna_sync_runtime
 from backend.recovery_108 import RecordedSync,sealed,hashed,read
 from backend.luna_budget import BudgetJournal
 from backend.luna_application import request_key
 folder=Path(folder);auth=read(folder/'authorization.json');manifest=read(folder/'manifest.json')
 if auth.get('explicit_user_approval')is not True or auth['manifest_sha256']!=hashed(folder/'manifest.json')or digest(manifest)!=campaign:raise ValueError('Exact campaign authorization required')
 from throughput_runtime import make_lab
 lab=make_lab(config);job=auth['job'];owner='direct-recovery-'+str(os.getpid());fence=Fence(Path(config['fences'])/(job+'.worker.lock'))
 acquired=fence.acquire()
 for _ in range(50):
  if acquired:break
  time.sleep(.1);acquired=fence.acquire()
 if not acquired:raise RuntimeError('Worker already active')
 try:
  from backend.luna_credentials import load
  os.environ['OPENAI_PROJECT']=config['openai_project']
  if not load():raise RuntimeError('Credential unavailable')
  with lab.tx()as c:
   row=c.execute('select owner,status from jobs where id=?',(job,)).fetchone()
   if row['owner']is not None:raise ValueError('Foreign worker owner')
   c.execute("update jobs set owner=?,status='running' where id=?",(owner,job))
  cases={c['id']:c for c in manifest['cases']};requests={digest(r['body']):r for r in manifest['requests']}
  class Provider:
   simulation_only=False
   def __init__(self):self.transports={}
   def prepare(self,body):
    key=digest(body);row=requests[key];assert body==row['body']and row['id']in auth['allowed_ids']
    native=folder/'native'/row['id'];native.mkdir(parents=True,exist_ok=True)
    m=dict(reader_sha256=hashed(Path(reader.__file__)),runtime_sources={n:hashed(Path(mod.__file__))for n,mod in [('luna_reader',reader),('luna_runner',luna_runner),('luna_sync_runtime',luna_sync_runtime)]},allowed_experiment_ids=[manifest['experiment']],requests=[row]);sealed(native/'manifest.json',m)
    cap=reader.estimate_reserve(body,'sync')['reserved_usd'];journal=native/'budget.json';BudgetJournal(journal).initialize(cap_usd=cap,prior_evidence='Mirror of coordinator reservation')
    a=dict(mode='sync',model=reader.MODEL,explicit_user_approval=True,scope='blocked-direct-recovery',manifest_path=str(native/'manifest.json'),sealed_manifest_sha256=hashed(native/'manifest.json'),allowed_experiment_ids=[manifest['experiment']],private_directory=str(native),budget_journal=str(journal),run_id=campaign+'-'+row['id'],max_requests=1,max_usd=cap,allow_definitive_950=False);sealed(native/'authorization.json',a);self.transports[key]=RecordedSync(native/'authorization.json')
   def __call__(self,body):
    key=digest(body);row=requests[key];raw=self.transports[key](body,row['endpoint']);nativekey=request_key(body,row['endpoint'])[0];receipt=read(folder/'native'/row['id']/(nativekey+'.receipt.json'));return receipt['actual_usd'],raw,{}
  provider=Provider()
  # Recover a paid receipt committed before a worker crash without another call.
  for key,row in requests.items():
   if row['id']not in auth['allowed_ids']:continue
   with lab.connect()as c:saved=c.execute('select status,receipt from requests where key=?',(key,)).fetchone()
   with connect(db)as c:exists=c.execute('select 1 from decisions where campaign=? and id=?',(campaign,row['id'])).fetchone()
   if saved['status']=='completed'and not exists:
    raw=json.loads(saved['receipt'])
    try:
     if raw['choices'][0]['finish_reason']!='stop':raise ValueError('incomplete')
     proposal=json.loads(raw['choices'][0]['message']['content'])
    except (ValueError,KeyError,IndexError,TypeError):proposal={'invalid_raw_output':True}
    store(db,campaign,cases[row['id']],proposal,folder/'native'/row['id'])
  def publish(result):
   row=requests[result['key']];case=cases[row['id']]
   if result['state']=='completed':
    with lab.connect()as c:raw=json.loads(c.execute('select receipt from requests where key=?',(result['key'],)).fetchone()[0])
    try:
     if len(raw['choices'])!=1 or raw['choices'][0]['finish_reason']!='stop':raise ValueError('incomplete output')
     proposal=json.loads(raw['choices'][0]['message']['content'])
    except (ValueError,KeyError,IndexError,TypeError):proposal={'invalid_raw_output':True}
    store(db,campaign,case,proposal,folder/'native'/case['id'])
   else:
    with connect(db)as c:c.execute('insert or replace into progress values(?,?,?,?)',(campaign,case['id'],result['state'],time.time()))
  if config.get('throughput_runtime')=='continuous12-v1':
   with lab.connect()as c:ready=[key for key,row in requests.items()if row['id']in auth['allowed_ids']and c.execute('select status from requests where key=?',(key,)).fetchone()['status']=='ready']
   if ready:lab.stream(job,owner,ready,provider,config['wire'],stop=lambda:(folder/'stop.requested').exists(),on_result=publish)
  else:
   while True:
    with lab.connect()as c:ready=[key for key,row in requests.items()if row['id']in auth['allowed_ids']and c.execute('select status from requests where key=?',(key,)).fetchone()['status']=='ready']
    if not ready:break
    results=lab.execute_batch(job,owner,ready[:2],provider,config['wire'],token_bound=lambda b:reader.estimate_reserve(b,'sync')['estimated_input_token_bound']+b['max_completion_tokens'],retain_owner_on_failure=True)
    if not results:break
    print(json.dumps({'batch_finished':time.time(),'completed':sum(r['state']=='completed'for r in results),'states':[r['state']for r in results]}),flush=True)
    for result in results:
     row=requests[result['key']];case=cases[row['id']]
     if result['state']=='completed':
      with lab.connect()as c:raw=json.loads(c.execute('select receipt from requests where key=?',(result['key'],)).fetchone()[0])
      try:
       if len(raw['choices'])!=1 or raw['choices'][0]['finish_reason']!='stop':raise ValueError('incomplete output')
       proposal=json.loads(raw['choices'][0]['message']['content'])
      except (ValueError,KeyError,IndexError,TypeError):proposal={'invalid_raw_output':True}
      store(db,campaign,case,proposal,folder/'native'/case['id'])
     else:
      with connect(db)as c:c.execute('insert or replace into progress values(?,?,?,?)',(campaign,case['id'],result['state'],time.time()))
    # Invalid semantic decisions and uncertain transmissions do not stop independent ready cases.
    if all(r['state']=='pre_send_stopped'for r in results):break
 finally:
  # Exhausted direct attempts become visible No evaluado, not a job-wide stall.
  # Their uncertain monetary reserve and original transport evidence remain held.
  if 'requests' in locals():
   for key,row in requests.items():
    if row['id'] not in auth['allowed_ids']:continue
    with lab.connect()as c:state=c.execute('select status from requests where key=?',(key,)).fetchone()[0]
    if state!='uncertain':continue
    store(db,campaign,cases[row['id']],{'transport_failure':'uncertain_no_retry'},folder/'native'/row['id'])
    with lab.tx()as c:
     from partial_transport_closure import initialize
     initialize(c)
     c.execute('insert or ignore into evaluation_transport_closures values(?,?,?,?,?)',(job,str(cases[row['id']]['response_id']),key,'Direct attempt exhausted: No evaluado; no retry and reserve retained',time.time()))
  with lab.tx()as c:
   c.execute('CREATE TABLE IF NOT EXISTS partial_closures(job TEXT,response TEXT,request_key TEXT,reason TEXT,created REAL,PRIMARY KEY(job,response))')
   from partial_transport_closure import initialize
   initialize(c)
   # Explicit evaluation closure does not fabricate a receipt, release the held
   # reserve, or permit retransmission of the uncertain original request.
   pending=c.execute("select 1 from requests r where job=? and status in ('sending','uncertain') and not exists(select 1 from partial_closures p where p.job=r.job and p.request_key=r.key) and not exists(select 1 from evaluation_transport_closures p where p.job=r.job and p.request_key=r.key)",(job,)).fetchone()
   ready=c.execute("select 1 from requests where job=? and status='ready'",(job,)).fetchone()
   c.execute('update jobs set status=?,owner=NULL where id=? and owner=?',('pending_reconciliation'if pending else 'stopped_requires_review'if ready else 'complete',job,owner))
  fence.release()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--campaign',required=True);p.add_argument('--database',required=True);p.add_argument('--folder',required=True);a=p.parse_args();run(json.loads(Path(a.config).read_text(encoding='utf8')),a.campaign,a.database,a.folder)
