import json
from copy import deepcopy
from pathlib import Path
from decimal import Decimal
from backend import luna_reader as reader
from backend.luna_qualification import verify_certificate

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'docs/economic_readers_step3_2_20261016/adjudicated_final_20261016'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def rows():
 tag='v'+reader.VERSION.rsplit('-',1)[1]
 return read(DATA/f'native_{tag}/ALL_REQUESTS_{tag}.json')

def test_followup_af7_is_exact_case_gate_only_and_does_not_change_contract():
 row=next(r for r in rows() if r['endpoint']=='chat/completions' and set(json.loads(r['body']['messages'][1]['content'])['indicators'])=={'AF7'})
 p=json.loads(row['body']['messages'][1]['content'])
 assert p['reported_professional_adjudications']['reported_answer']=='Así es'
 assert 'No acredita B/T/M' in p['reported_professional_adjudications']['scope']
 from backend.evaluators.ansiedad_semantic.budgeted_reader import envelope
 for field in ('user','response','prior_history'):
  changed=deepcopy(p);changed.pop('reported_professional_adjudications')
  changed['original'][field]=[{'role':'user','text':'different history'}] if field=='prior_history' else changed['original'][field]+' Otra frase.'
  body=reader.adapt_body(envelope(changed,reader.MODEL),'ansiedad_depresion',changed['stage'])
  assert 'reported_professional_adjudications' not in json.loads(body['messages'][1]['content'])

def test_followup_re1_never_ratifies_missing_functional_threshold():
 assert 'NO confirma umbral funcional' in reader._FOLLOWUP_RE1['scope']
 assert 'En todos los casos' in reader._FOLLOWUP_RE1['reported_answer']
 body=next(r['body'] for r in rows() if r['endpoint']=='responses' and {d['code'] for d in json.loads(r['body']['input'][1]['content'])['predicates'].values()}=={'CR-RE1'})
 p=json.loads(body['input'][1]['content'])
 assert p['reported_professional_adjudications']['followup_clarification']==reader._FOLLOWUP_RE1
 assert 'obstaculizar' in p['official_gates']['CR-RE1']

def test_fixed_own_crisis_scope_routing_preserves_other_observations_and_literal_sources():
 body=next(r['body'] for r in rows() if r['endpoint']=='responses' and len({d['code'] for d in json.loads(r['body']['input'][1]['content'])['predicates'].values()})>1 and 'CR-NI9.gate' in json.loads(r['body']['input'][1]['content'])['predicates'])
 p=json.loads(body['input'][1]['content']);seen=[]
 def transport(request,endpoint):
  payload=json.loads(request['input'][1]['content']);codes={d['code'] for d in payload['predicates'].values()};seen.append((codes,payload['conversation']))
  is_own=len(codes)==1
  lib=payload['literal_spans'];ai=next(k for k,v in lib.items() if v['source']=='current_ai');user=next(k for k,v in lib.items() if v['source']=='current_user')
  claims={k:dict(observation='absent' if is_own else 'present',evidence=[] if is_own else [ai],context=[user],reason='Routing fixture, not semantic evidence.') for k in payload['predicates']}
  wire=dict(reviewed_entire_context=True,claims=claims)
  return dict(model=reader.MODEL,status='completed',output=[dict(type='message',role='assistant',phase='final_answer',status='completed',content=[dict(type='output_text',text=json.dumps(wire))])])
 provider=reader.LunaProvider(transport)
 result=provider.run('extract','',p,{},list(p['predicates']),{})
 target=reader.ISOLATED_CRISIS_CODES.intersection(d['code'] for d in p['predicates'].values())
 assert len(seen)==1+len(target)
 assert all(q==p['conversation'] for _,q in seen)
 for claim in result['claims']:
  code=claim['id'].split('.')[0]
  assert claim['state']==('no' if code in target else 'yes')

def test_both_blind_stages_have_identical_own_scopes_and_unchanged_originals():
 scopes={}
 for r in rows():
  b=r['body'];p=json.loads(b.get('input',b.get('messages'))[1]['content'])
  codes=set(p['indicators']) if 'indicators' in p else {d['code'] for d in p['predicates'].values()}
  if len(codes)!=1:continue
  code=next(iter(codes))
  if code not in {'AF6','AF7','PA8','ND7'}|reader.ISOLATED_CRISIS_CODES:continue
  scopes.setdefault(code,[]).append(p)
 assert set(scopes)=={'AF6','AF7','PA8','ND7'}|reader.ISOLATED_CRISIS_CODES
 for code,pair in scopes.items():
  assert len(pair)==2
  assert pair[0].get('original',pair[0].get('conversation'))==pair[1].get('original',pair[1].get('conversation'))
  assert pair[0].get('indicators',pair[0].get('predicates'))==pair[1].get('indicators',pair[1].get('predicates'))

def test_existing_own_qualification_bodies_still_verify_and_no_uncertain_body_is_planned():
 p=reader.LunaProvider(None)
 tag='v'+reader.VERSION.rsplit('-',1)[1]
 assert all(verify_certificate(p,c,proof) for c,proof in read(DATA/f'qualification_{tag}/CERTIFICATES_COMPATIBLE_V7.json').items())
 forbidden={'5ef1a01c4b73c77e79d2bb3d0a01e960bfd15a7443d54d2c158ee317852eb944','6b13d0d68c47880c06d62f0bcc77c79c2309c7353edb22796f365c093d0082dd'}
 from backend.luna_application import request_key
 assert not forbidden.intersection(request_key(r['body'],r['endpoint'])[0] for r in rows())
 assert read(DATA/f'native_{tag}/CAPTURE_SUMMARY_{tag}.json')['exact_reused']==54
 reserve=sum(Decimal(read(DATA/n/'PREFLIGHT.json')['reserve_usd']) for n in ('native_final_AN_v17','native_final_CR_v17','controls_remaining_v17'))
 assert reserve<Decimal(read(DATA/'followup_v17/BALANCE_BEFORE.json')['remaining_usd'])

def test_followup_criteria_do_not_invalidate_unaffected_mixed_package_evidence():
 own_af=own_re=0
 for row in rows():
  b=row['body'];p=json.loads(b.get('input',b.get('messages'))[1]['content'])
  if row['endpoint']=='chat/completions' and 'AF7' in p['indicators']:
   if len(p['indicators'])>1:assert 'reported_professional_adjudications' not in p
   else:assert p['reported_professional_adjudications']==reader._FOLLOWUP_AF7;own_af+=1
  if row['endpoint']=='responses' and 'CR-RE1.gate' in p['predicates']:
   criteria=p['reported_professional_adjudications']
   if len({d['code'] for d in p['predicates'].values()})>1:assert 'followup_clarification' not in criteria
   else:assert criteria['followup_clarification']==reader._FOLLOWUP_RE1;own_re+=1
 assert own_af==own_re==2
