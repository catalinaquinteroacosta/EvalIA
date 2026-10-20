"""Focal v7 regression: immutable contracts, real referents and carried authority."""
import json
from pathlib import Path
from backend import luna_reader as reader
from backend.luna_qualification import verify_certificate
from crisis_semantic.predicate_catalog import definitions
from backend.evaluators.transversal_candidate_v1.adenda_ri2_v11 import final_definitions
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/economic_readers_step3_2_20261016/semantic_final_v7'
CERT=OUT.parent/f"adjudicated_final_20261016/qualification_v{reader.VERSION.rsplit('-',1)[1]}/CERTIFICATES_COMPATIBLE_V7.json"
def read(p):return json.loads(p.read_text(encoding='utf8'))
def test_v7_own_certificates_rebind_only_if_effective_requests_unchanged():
 p=reader.LunaProvider(None)
 for code,proof in read(CERT).items():
  assert verify_certificate(p,code,proof)
  proof['identity']['prompt_sha256']='wrong';assert not verify_certificate(p,code,proof)
def test_focal_cr_preserves_official_definitions_and_complete_authentic_context():
 p=reader.LunaProvider(None);original=read(OUT.parent/'closure_final_20261016/native_v6/CASES.json')[1]['record']['originals'][0]
 for row in read(OUT/'authentic_CR/MANIFEST.json')['requests']:
  payload=json.loads(row['body']['input'][1]['content'])
  assert payload['predicates']==final_definitions(definitions(p.contracts,row['codes']))
  assert payload['conversation']['current_user']==original['user']
  assert payload['conversation']['current_ai']==original['response']
  assert payload['conversation']['history']==[]
def test_controls_are_separate_and_have_positive_negative_and_boundary_evidence():
 rows=read(OUT/'controls_RI1_PA6/MANIFEST.json')['requests'];assert len(rows)==16
 assert all(r['synthetic_control_not_authentic_bank_response'] is True for r in rows)
 assert len({r['case_id'] for r in rows})==8
 assert all(sum(r['case_id']==c for r in rows)==2 for c in {r['case_id'] for r in rows})
def test_no_additional_grant_and_no_uncertain_key_in_all_sealed_requests():
 from backend.luna_application import request_key
 keys=[]
 for name in ('authentic_AN','authentic_CR','controls_RI1_PA6'):
  a=read(OUT/name/'AUTHORIZATION.json');assert a['additional_authorization_usd']=='0' and a['allow_definitive_950'] is False
  assert Path(a['inherited_authorization']['path']).name=='ORDER_AUTHORIZATION_2USD.json'
  for r in read(OUT/name/'MANIFEST.json')['requests']:
   b=r['body'];assert b['store'] is False and b['model']==reader.MODEL
   assert b.get('reasoning',{}).get('effort',b.get('reasoning_effort'))=='none'
   keys.append(request_key(b,r['endpoint'])[0])
 assert len(keys)==len(set(keys))==26
 for key in ('5ef1a01c4b73c77e79d2bb3d0a01e960bfd15a7443d54d2c158ee317852eb944','6b13d0d68c47880c06d62f0bcc77c79c2309c7353edb22796f365c093d0082dd'):assert key not in keys
def test_qualified_special_code_prompts_have_no_changed_scoped_text():
 # Exact bodies inside the certified original lineage remain the source of truth.
 for code in ('CR-RI2','CR-CE10'):
  proof=read(CERT)[code]
  assert proof['identity']['prompt_sha256']==proof['previous_identity']['prompt_sha256']

def test_new_original_receipts_and_reference_checks_cover_all_36_calls():
 from hashlib import sha256
 from backend.luna_application import request_key
 from backend.luna_reader import usage_cost
 delivery=OUT.parent/'semantic_final_delivery_20261016'
 evidence=read(delivery/'SEMANTIC_EVIDENCE.json');assert len(evidence)==36
 seen=set()
 for row in evidence:
  r=row['request'];key=request_key(r['body'],r['endpoint'])[0];assert key not in seen;seen.add(key)
  receipt=read(Path(row['receipt']['path']));rawpath=Path(row['raw_response']['path']);raw=read(rawpath)
  assert receipt['response_sha256']==sha256(rawpath.read_bytes()).hexdigest()
  assert receipt['http_status']==200 and receipt['remote_request_id']
  assert str(usage_cost(raw,'sync'))==receipt['actual_usd']
 controls=read(delivery/'CONTROLS_REVIEW.json')
 assert len(controls)==8 and all(c['exact_body_compatible_with_v9'] and c['paired'] for c in controls)
