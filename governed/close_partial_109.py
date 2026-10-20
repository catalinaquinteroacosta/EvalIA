"""Explicit offline closure of #109's timed-out reader; never resends it."""
import sys,json,sqlite3,hashlib,time,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'governed'),str(ROOT/'venv/Lib/site-packages')]
def run(apply=False):
 cfg=json.loads((ROOT/'.evalia-private/governed_joint_install_20261017/config.json').read_text())
 from governed_parallel import GovernedLab
 from backend import main,database
 from backend.integrated_evaluation import authoritative_record,compatible_result,save_review
 from backend import luna_runner,luna_reader
 from backend.luna_application import BatchPending
 lab=GovernedLab(cfg['coordinator'])
 def connection():
  c=sqlite3.connect(cfg['database']);c.row_factory=sqlite3.Row;return c
 main.get_connection=connection;database.DB_PATH=Path(cfg['database'])
 with lab.connect()as c:
  job=dict(c.execute('select * from jobs where experiment=109').fetchone())
  assert job['owner'] is None
  pending=c.execute("select key,status,body from requests where job=? and status!='completed'",(job['id'],)).fetchall()
  assert len(pending)==1 and pending[0]['status']=='uncertain'
  key=pending[0]['key']
  contracts=c.execute('select response,keys_json from response_contracts where job=?',(job['id'],)).fetchall()
  target=[r for r in contracts if key in json.loads(r['keys_json'])];assert len(target)==1
  rid=int(target[0]['response']);keys=json.loads(target[0]['keys_json'])
  before={r['response']:r['payload_hash'] for r in c.execute('select response,payload_hash from results where job=?',(job['id'],))}
 record=authoritative_record(main,main._get_response_context(rid));used=set()
 def replay(body,endpoint):
  k=hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
  assert k in keys
  if k==key:raise BatchPending([k])
  with lab.connect()as c:r=c.execute('select * from requests where key=?',(k,)).fetchone()
  assert r['status']=='completed' and hashlib.sha256(r['receipt'].encode()).hexdigest()==r['receipt_hash']
  used.add(k);return json.loads(r['receipt'])
 factory=luna_runner.IntegrationRunner
 provider=luna_reader.LunaProvider(replay,certificates=json.loads(Path(cfg['certificates']).read_text()))
 anxiety=lambda req:luna_reader.read_anxiety(req,replay)
 selected=factory(lambda _:record,crisis_provider=provider,anxiety_reader=anxiety).evaluate_response(rid)
 internal,public,complete=compatible_result(selected);assert not complete
 payload=dict(experiment=109,model=record['model'],turn=record['turn'],result=public,source_status='partial_transport_failure',transport_exception=dict(key=key,status='uncertain_no_retry',receipt_missing=True,held_reserve_preserved=True),native=selected)
 # Native rows are needed by the existing direct-recovery adapter.
 payload['result']['indicator_results']=selected['indicator_results']
 report=dict(response_id=rid,model=record['model'],turn=record['turn'],replayed_reads=len(used),rows=len(selected['indicator_results']),blocked=sum(r['status']=='BLOCKED' for r in selected['indicator_results']),paid_calls=0)
 if apply:
  wire=json.dumps(payload,sort_keys=True,ensure_ascii=False);digest=hashlib.sha256(wire.encode()).hexdigest()
  with lab.tx()as c:
   assert c.execute('select owner from jobs where id=?',(job['id'],)).fetchone()[0] is None
   assert not c.execute('select 1 from results where job=? and response=?',(job['id'],str(rid))).fetchone()
   c.execute('CREATE TABLE IF NOT EXISTS partial_closures(job TEXT,response TEXT,request_key TEXT,reason TEXT,created REAL,PRIMARY KEY(job,response))')
   c.execute('insert into partial_closures values(?,?,?,?,?)',(job['id'],str(rid),key,'Timeout: close evaluation without repeating uncertain transport; reserve retained',time.time()))
   c.execute('insert into results values(?,?,?,?)',(job['id'],str(rid),wire,digest))
   after={r['response']:r['payload_hash'] for r in c.execute('select response,payload_hash from results where job=?',(job['id'],))}
   assert all(after[k]==v for k,v in before.items())
  save_review(main,rid,public)
  root=ROOT/'.evalia-private/direct_recovery'
  from direct_recovery import prepare
  cid,manifest=prepare(cfg,109,root/'recovery.db',root/'109')
  report.update(campaign=cid,recovery_calls=manifest['max_calls'],preventive_cost_usd=manifest['estimate_usd'])
 print(json.dumps(report))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');run(p.parse_args().apply)
