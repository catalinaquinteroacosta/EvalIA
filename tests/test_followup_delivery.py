import json
from pathlib import Path
from decimal import Decimal
from hashlib import sha256
from backend.luna_application import request_key

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'docs/economic_readers_step3_2_20261016/adjudicated_final_20261016'
OUT=DATA/'followup_v17/ENTREGA_FINAL'
def read(p):return json.loads(p.read_text(encoding='utf8'))

def test_current_persisted_inventory_resolves_eight_and_keeps_only_two_legitimate_blocks():
 rows=read(OUT/'INVENTARIO_185_FINAL.json')['indicators']
 assert len(rows)==len({r['code'] for r in rows})==185
 assert {r['code'] for r in rows if r['status']=='BLOCKED'}=={'CR-RE1','CR-AC6'}
 expected={'AF6':('SCORED',0),'AF7':('SCORED',2),'PA8':('SCORED',0),'ND7':('SCORED',3),'CR-NI9':('N/A',None),'CR-CT10':('SCORED',3),'CR-PP5':('SCORED',3),'CR-RE7':('SCORED',3),'CR-RE1':('BLOCKED',None),'CR-AC6':('BLOCKED',None)}
 for r in rows:
  if r['code'] in expected:assert (r['status'],r['score'])==expected[r['code']]
  if r['status']!='SCORED':assert r['score'] is None
 stored=[]
 from backend.export_audit import indicator_records
 for eid in (99,101):stored+=indicator_records(read(DATA/f'native_v19/RESULTS_{eid}.json'))
 assert {r['code']:(r['status'],r['score']) for r in rows}=={r['code']:(r['status'],r['score']) for r in stored}

def test_all_new_receipts_reconcile_to_original_grant_without_retransmission():
 record=read(OUT/'COSTOS_Y_SALDO.json');receipts=record['receipts']
 assert record['new_calls']==record['complete_valid_responses']==len(receipts)==66
 assert record['new_uncertain']==record['new_truncated']==0
 assert len({r['key'] for r in receipts})==66
 oldkeys={r['key'] for r in read(DATA/'delivery_v16/COSTOS_Y_SALDO_FINAL.json')['receipts']}
 assert not oldkeys.intersection(r['key'] for r in receipts)
 total=sum((Decimal(r['actual_usd']) for r in receipts),Decimal(0))
 assert total==Decimal(record['new_spend_usd'])
 assert Decimal(record['before']['remaining_usd'])-total==Decimal(record['after']['remaining_usd'])
 assert record['before']['reserved_usd']==record['after']['reserved_usd']=='0.10656250'
 assert record['additional_authorization_usd']=='0'
 for row in receipts:
  for field in ('receipt','response'):
   artifact=row[field];assert sha256(Path(artifact['path']).read_bytes()).hexdigest()==artifact['sha256']

def test_exact_replay_and_unaffected_parent_bodies_reuse_v16_without_new_inference():
 final=read(DATA/'native_v19/HTTP_INTEGRATION_FINAL.json')
 assert final['exact_original_requests_used']==56 and final['new_API_calls']==0
 current=read(DATA/'native_v19/ALL_REQUESTS_v19.json');old=read(DATA/'native_v16/ALL_REQUESTS_v16.json')
 oldkeys={request_key(r['body'],r['endpoint'])[0] for r in old}
 checked_af=checked_re=0
 for row in current:
  body=row['body'];p=json.loads(body.get('input',body.get('messages'))[1]['content'])
  if row['endpoint']=='chat/completions' and len(p['indicators'])>1 and 'AF7' in p['indicators']:
   assert request_key(body,row['endpoint'])[0] in oldkeys;checked_af+=1
  if row['endpoint']=='responses' and 'CR-RE1.gate' in p['predicates'] and len({d['code'] for d in p['predicates'].values()})>1:
   assert request_key(body,row['endpoint'])[0] in oldkeys;checked_re+=1
 assert checked_af==checked_re==2
 controls=read(OUT/'CONTROLES_EFECTIVOS.json')
 assert len(controls)==18 and all(c['passed'] and c['synthetic_not_bank'] for c in controls)
 assert all(len(c['request_keys'])==2 for c in controls)
