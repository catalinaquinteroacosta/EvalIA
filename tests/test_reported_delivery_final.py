"""Final persisted evidence checks; no network and no score rewriting."""
import json
from pathlib import Path
from decimal import Decimal
from hashlib import sha256

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'docs/economic_readers_step3_2_20261016/adjudicated_final_20261016'
OUT=BASE/'delivery_v16'
def read(p):return json.loads(p.read_text(encoding='utf8'))

def test_complete_inventory_keeps_unresolved_rows_and_no_fabricated_global():
 rows=read(OUT/'INVENTARIO_185_FINAL.json')['indicators']
 assert len(rows)==len({r['code'] for r in rows})==185
 assert sum(r['status']=='SCORED' for r in rows)==144
 assert sum(r['status']=='N/A' for r in rows)==31
 assert sum(r['status']=='BLOCKED' for r in rows)==10
 assert all(r['score'] is None for r in rows if r['status']!='SCORED')
 assert all(Path(r['audit_source']).exists() for r in rows)
 record=read(BASE/'native_v16/HTTP_INTEGRATION_FINAL.json')
 assert record['exact_original_requests_used']==42 and record['new_API_calls']==0

def test_reported_decisions_match_persisted_python_scores_without_claiming_expert_grades():
 states=read(OUT/'ESTADO_SIETE_ADJUDICACIONES.json')
 assert {s['code']:s['score'] for s in states}=={'CR-NI4':3,'CR-NI7':0,'CR-PP1':0,'CR-RE1':None,'CR-RE8':3,'CR-CE3':3,'CR-OP1':3}
 assert all(s['score']==s['native_result']['score'] and not s['manual_score_override'] for s in states)
 assert all(s['professional_identity'] is None and s['consultation_date'] is None for s in states)
 assert 'opposite' in next(s for s in states if s['code']=='CR-NI7')['technical_review']
 verdict=read(OUT/'DICTAMEN_MAQUINA.json')
 assert verdict['verdict']=='NO APTO' and verdict['definitive_950_executed']==0

def test_all_new_costs_include_truncations_and_keep_historical_uncertainty_reserved():
 costs=read(OUT/'COSTOS_Y_SALDO_FINAL.json');receipts=costs['receipts']
 assert costs['new_calls']==len(receipts)==76
 assert costs['valid_complete']==74 and costs['truncated_known_cost']==2 and costs['new_uncertain']==0
 assert len({r['key'] for r in receipts})==76
 total=sum((Decimal(r['cost_usd']) for r in receipts),Decimal(0))
 assert total==Decimal(costs['new_spend_usd'])
 assert Decimal(costs['before']['remaining_usd'])-total==Decimal(costs['after']['remaining_usd'])
 assert costs['before']['reserved_usd']==costs['after']['reserved_usd']=='0.10656250'
 for row in receipts:
  for key in ('receipt','raw_response'):
   a=row[key];assert sha256(Path(a['path']).read_bytes()).hexdigest()==a['sha256']
 forbidden={'5ef1a01c4b73c77e79d2bb3d0a01e960bfd15a7443d54d2c158ee317852eb944','6b13d0d68c47880c06d62f0bcc77c79c2309c7353edb22796f365c093d0082dd'}
 assert not forbidden.intersection(r['key'] for r in receipts)

def test_effective_positive_negative_and_boundary_controls_are_real_paired_receipts():
 cases=read(OUT/'CONTROLES_PA6_EFECTIVOS.json')
 assert len(cases)==4 and all(len(c['paired'])==2 and c['synthetic_not_authentic_bank'] for c in cases)
 assert [c['result']['score'] for c in cases]==[3,0,0,3]
 cr=read(OUT/'CONTROLES_FINALES.json')
 assert [(r['status'],r['score']) for r in cr]==[('SCORED',3),('SCORED',0),('SCORED',3),('N/A',None)]
