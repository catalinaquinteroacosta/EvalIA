"""Offline prepare and reuse only already-paid valid direct BLOCKED decisions."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'governed'),str(ROOT/'venv/Lib/site-packages')]
from direct_recovery import prepare,connect,store,wire,consolidated,digest
def main():
 config=json.loads((ROOT/'.evalia-private/governed_joint_install_20261017/config.json').read_text(encoding='utf8'));root=ROOT/'.evalia-private/direct_recovery';db=root/'recovery.db';cid,m=prepare(config,108,db,root/'108')
 b=ROOT/'.evalia-private/blind_comparison_108_20261017';decisions=json.loads((b/'direct_real_v1/METHOD_B_RESULTS.json').read_text(encoding='utf8'));mapping={r['blind_id']:r for r in json.loads((b/'MAPPING_PRIVATE.json').read_text(encoding='utf8'))};blind={c['id']:c for c in json.loads((ROOT/'isolated_concurrency_step1_20261016/blind_comparison_108_20261017/BLIND_CASES.json').read_text(encoding='utf8'))}
 originals={}
 with connect(config['coordinator'])as c:
  for row in c.execute("select response,payload from results where response not like 'adjudication:%'"):
   p=json.loads(row['payload']);originals[(p['model'],p['turn'])]=int(row['response'])
 reused=0
 for p in decisions:
  maprow=mapping[p['id']]
  if maprow['original_status']!='BLOCKED'or p['status']not in ('SCORED','N/A'):continue
  rid=originals[(maprow['model'],maprow['turn'])];case=next(c for c in m['cases']if c['response_id']==rid and c['code']==maprow['indicator']);bc=blind[p['id']]
  assert case['sources']['user']==bc['user']and case['sources']['response']==bc['response']
  assert [case['sources'][f'history_{i}']for i in range(len(bc['history']))]==[h['text']for h in bc['history']]
  proposal={k:p[k]for k in ['status','applicable','score','justification','upper_contrast']};proposal['id']=case['id'];proposal['evidence']=[dict(source='history_'+str(q['history_index'])if q['source']=='history'else q['source'],quote=q['quote'])for q in p['evidence']]
  store(db,cid,case,proposal,b/'direct_real_v1/native'/p['id']);reused+=1
 with connect(db)as c:done={r['id']for r in c.execute('select id from decisions where campaign=?',(cid,))}
 from decimal import Decimal
 pending=[r for r in m['requests']if r['id']not in done];estimate=sum(Decimal(r['reserved_usd'])for r in pending)
 data=consolidated(config,108,db);summary=dict(campaign=cid,original_blocked=len(m['cases']),reused_paid_results=reused,new_calls_required=len(pending),max_preventive_usd=str(estimate),summary=data['summary'],calls_sent_now=0)
 (root/'108/READY.json').write_text(wire(summary),encoding='utf8');print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
