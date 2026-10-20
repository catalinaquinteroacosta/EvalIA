"""Close terminal reader failures without receipts, invented grades or retransmission."""
import json,hashlib,time
from pathlib import Path

def initialize(c):
 c.execute('CREATE TABLE IF NOT EXISTS evaluation_transport_closures(job TEXT,response TEXT,request_key TEXT PRIMARY KEY,reason TEXT,created REAL)')

def close_missing(main,lab,job,info,certificates,owner=None):
 from backend.integrated_evaluation import authoritative_record,compatible_result,save_review
 from backend import luna_reader,luna_runner
 from backend.luna_application import BatchPending
 from backend.evaluation_engine import EvaluationEngine
 with lab.connect()as c:
  state=c.execute('select experiment,owner from jobs where id=?',(job,)).fetchone()
  if state['experiment']==72:raise ValueError('Protected experiment')
  if state['owner']!=owner:raise ValueError('Foreign closure owner')
  if c.execute("select 1 from requests where job=? and status in ('ready','reserved','sending')",(job,)).fetchone():return False
  contracts=c.execute('select response,keys_json from response_contracts where job=?',(job,)).fetchall()
 manifest=Path(info['manifest']).read_bytes()
 if hashlib.sha256(manifest).hexdigest()!=info['manifest_sha256']:raise ValueError('Changed manifest')
 release=json.loads(manifest).get('reader_version')
 for contract in contracts:
  rid=int(contract['response']);keys=json.loads(contract['keys_json'])
  if lab.load_result(job,str(rid)) is not None:continue
  record=authoritative_record(main,main._get_response_context(rid));missing=[]
  def replay(body,endpoint):
   key=hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
   if key not in keys:raise ValueError('Foreign replay request')
   with lab.connect()as c:r=c.execute('select * from requests where key=? and job=?',(key,job)).fetchone()
   if r['status']!='completed':
    if r['status'] not in ('uncertain','skipped_no_send'):raise ValueError('Nonterminal request')
    raise BatchPending([key])
   if hashlib.sha256(r['receipt'].encode()).hexdigest()!=r['receipt_hash']:raise ValueError('Receipt changed')
   return json.loads(r['receipt'])
  with lab.connect()as c:missing=[k for k in keys if c.execute('select status from requests where key=?',(k,)).fetchone()[0]!='completed']
  if not missing:raise ValueError('Missing result without transport failure')
  if release=='LUNA-LITERAL-STAGE0-20261017-1':
   from governed.double_resolution_v1.stage_zero import factories
   factory,provider,anxiety=factories(replay,certificates=certificates)
  else:
   factory=luna_runner.IntegrationRunner;provider=luna_reader.LunaProvider(replay,certificates=certificates);anxiety=lambda req:luna_reader.read_anxiety(req,replay)
  try:selected=factory(lambda _:record,crisis_provider=provider,anxiety_reader=anxiety).evaluate_response(rid)
  except BatchPending:
   # Some crisis readers cannot compose a partial result. Preserve all receipts
   # and route the official inventory to direct grading instead of assigning 0.
   engine=EvaluationEngine(record['rubric_type'])
   rows=[dict(code=k,family=engine.indicator_to_criterion[k],status='BLOCKED',score=None,reason='Lectura incompleta por fallo de transporte; requiere recuperación directa.') for k in engine.indicators_by_code]
   selected=dict(rubric_type=record['rubric_type'],indicator_results=rows,turn_number=record['turn'],engine='partial_transport_closure',aggregation={'global_v2':None})
  _,public,_=compatible_result(selected)
  payload=dict(experiment=info['experiment'],model=record['model'],turn=record['turn'],result=public,source_status='partial_transport_failure',transport_exceptions=missing,native=selected)
  payload['result']['indicator_results']=selected['indicator_results']
  wire=json.dumps(payload,sort_keys=True,ensure_ascii=False)
  with lab.tx()as c:
   if c.execute('select owner from jobs where id=?',(job,)).fetchone()[0]!=owner:raise ValueError('Owner changed')
   initialize(c)
   for key in missing:c.execute('insert or ignore into evaluation_transport_closures values(?,?,?,?,?)',(job,str(rid),key,'Terminal failure closed without retry; original receipt state and reserve preserved',time.time()))
   c.execute('insert into results values(?,?,?,?)',(job,str(rid),wire,hashlib.sha256(wire.encode()).hexdigest()))
  save_review(main,rid,public)
 with lab.tx()as c:
  missing=c.execute('select 1 from response_contracts r where job=? and not exists(select 1 from results s where s.job=r.job and s.response=r.response)',(job,)).fetchone()
  if missing:return False
  c.execute("update jobs set status='complete',owner=NULL where id=?",(job,))
 return True
