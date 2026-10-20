from copy import deepcopy
import json
from pathlib import Path
from backend import luna_reader as reader
from backend.luna_qualification import verify_certificate
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/economic_readers_step3_2_20261016/adjudicated_final_20261016'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def context():
 body=read(OUT/'reported_seven_pair/MANIFEST.json')['requests'][0]['body']
 return json.loads(body['input'][1]['content'])['conversation']
def test_case_specific_professional_criteria_do_not_leak_to_another_case_or_scope():
 q=context();assert reader.reported_adjudications(q,['CR-NI4'])['criteria']['CR-NI4']['reported_answer']=='Sí lo distingue'
 assert reader.reported_adjudications(q,['CR-RI2','CR-CE10']) is None
 for field in ('current_user','current_ai'):
  changed=deepcopy(q);changed[field]+=' Otra frase.';assert reader.reported_adjudications(changed,['CR-NI4']) is None
 changed=deepcopy(q);changed['current_turn']=2;assert reader.reported_adjudications(changed,['CR-NI7']) is None
 changed=deepcopy(q);changed['history']=[dict(number=0,user='previo',ai='previa',model='otro')];assert reader.reported_adjudications(changed,['CR-RE8']) is None
def test_both_blind_readers_get_same_reported_criteria_without_each_others_outputs():
 rows=read(OUT/'reported_seven_pair/MANIFEST.json')['requests'];a,b=[json.loads(r['body']['input'][1]['content']) for r in rows]
 assert a==b
 criteria=a['reported_professional_adjudications']
 assert criteria['not_manual_scores'] and len(criteria['criteria'])==7
 assert 'No ratifica' in criteria['criteria']['CR-RE1']['scope']
 assert 'sin SÍ/NO' in criteria['criteria']['CR-PP1']['scope']
 assert 'extractor' not in json.dumps(a['conversation'],ensure_ascii=False)
def test_certificates_still_verify_against_exact_effective_requests():
 provider=reader.LunaProvider(None)
 for code,proof in read(OUT/f"qualification_v{reader.VERSION.rsplit('-',1)[1]}/CERTIFICATES_COMPATIBLE_V7.json").items():assert verify_certificate(provider,code,proof)
def test_reported_provenance_does_not_invent_identity_signature_or_consultation_date():
 record=read(OUT/'ADJUDICACIONES_REPORTADAS.json')
 assert record['professional_name'] is None and record['professional_signature'] is None and record['consultation_date'] is None
 assert record['source']['sha256']==reader._REPORTED_SOURCE_SHA256

def test_final_native_composition_preserves_30_scopes_and_exact_reuse():
 tag='v'+reader.VERSION.rsplit('-',1)[1]
 folder='native' if tag=='v14' else 'native_'+tag
 capture=read(OUT/f'{folder}/CAPTURE_SUMMARY_{tag}.json');rows=read(OUT/f'{folder}/ALL_REQUESTS_{tag}.json')
 assert capture['total_requests']==len(rows)==56
 assert capture['exact_reused']==54 and capture['new_requests']==2
 assert sum(r['endpoint']=='chat/completions' for r in rows)==34
 assert sum(r['endpoint']=='responses' for r in rows)==22
def test_increased_output_limits_are_confined_to_demonstrated_failures():
 tag='v'+reader.VERSION.rsplit('-',1)[1]
 folder='native' if tag=='v14' else 'native_'+tag
 for r in read(OUT/f'{folder}/ALL_REQUESTS_{tag}.json'):
  b=r['body'];p=json.loads(b.get('input',b.get('messages'))[1]['content'])
  if r['endpoint']=='chat/completions':
   if set(p['indicators'])=={f'AF{i}' for i in range(1,9)} and p['stage']=='independent_verify':assert b['max_completion_tokens']==18000
  elif 'CR-RI1.a' in p['predicates']:assert b['max_output_tokens']==len(p['predicates'])*160+512
  elif len(p['predicates'])>100:assert b['max_output_tokens']==len(p['predicates'])*112+256
def test_external_documentation_is_case_scoped_and_does_not_leak_to_cs():
 tag='v'+reader.VERSION.rsplit('-',1)[1]
 cp=op=cs=0
 folder='native' if tag=='v14' else 'native_'+tag
 for r in read(OUT/f'{folder}/ALL_REQUESTS_{tag}.json'):
  p=json.loads(r['body'].get('input',r['body'].get('messages'))[1]['content'])
  if r['endpoint']=='chat/completions' and 'CP5' in p['indicators']:
   assert p['external_reference_provenance']==reader._DOCUMENTED_CP5_PROVENANCE;cp+=1
  if r['endpoint']=='responses' and 'CR-OP3.a' in p['predicates']:
   assert p['external_reference_provenance']==reader._DOCUMENTED_OP3_PROVENANCE
   assert 'CR-OP3.a' in p['external_attestations'];op+=1
  if r['endpoint']=='responses' and 'CR-CS1.a' in p['predicates']:
   assert not p['external_attestations'] and 'external_reference_provenance' not in p;cs+=1
 assert (cp,op,cs)==(2,2,2)

def test_isolation_keeps_whole_original_and_official_components_without_score_fields():
 from backend.luna_reader import isolated_anxiety_request
 tag='v'+reader.VERSION.rsplit('-',1)[1];rows=read(OUT/f'native_{tag}/ALL_REQUESTS_{tag}.json')
 payloads=[json.loads(r['body']['messages'][1]['content']) for r in rows if r['endpoint']=='chat/completions']
 for code in reader.ISOLATED_ANXIETY_CODES:
  full=next(p for p in payloads if code in p['indicators'] and len(p['indicators'])>1)
  narrow=isolated_anxiety_request(full,code)
  assert narrow['original']==full['original']
  assert narrow['indicators']=={code:full['indicators'][code]}
  assert narrow['stage']==full['stage']
  assert 'score' not in narrow and 'extractor_output' not in narrow

def test_isolation_scopes_are_fixed_before_reading_and_same_in_both_stages():
 tag='v'+reader.VERSION.rsplit('-',1)[1];rows=read(OUT/f'native_{tag}/ALL_REQUESTS_{tag}.json');scopes={}
 for r in rows:
  if r['endpoint']!='chat/completions':continue
  p=json.loads(r['body']['messages'][1]['content'])
  if len(p['indicators'])==1:
   code=next(iter(p['indicators']));scopes.setdefault(code,{})[p['stage']]=p
 assert set(scopes)==reader.ISOLATED_ANXIETY_CODES
 for code,pair in scopes.items():
  assert set(pair)=={'extract','independent_verify'}
  assert pair['extract']['original']==pair['independent_verify']['original']
  assert pair['extract']['indicators']==pair['independent_verify']['indicators']
  for stage in pair:
   body=next(r['body'] for r in rows if r['endpoint']=='chat/completions' and json.loads(r['body']['messages'][1]['content'])==pair[stage])
   assert body['reasoning_effort']=='low' and body['max_completion_tokens']>=6000

def test_synchronous_product_mount_uses_same_scoped_reader_as_integration(monkeypatch):
 from types import SimpleNamespace
 from backend import luna_sync_runtime as runtime
 transport=SimpleNamespace(config={'allowed_experiment_ids':[99,101],'run_id':'offline'},lock=object())
 monkeypatch.setattr(runtime,'SealedSyncTransport',lambda _:transport)
 seen=[]
 monkeypatch.setattr(reader,'read_anxiety',lambda request,t:seen.append((request,t)) or {'indicators':{}})
 app=SimpleNamespace(state=SimpleNamespace());runtime.configure(app,'offline-no-file')
 request={'stage':'independent_verify','original':{'user':'u','response':'a'}}
 app.state.evaluation_dependencies['anxiety_reader'](request)
 assert seen==[(request,transport)]
