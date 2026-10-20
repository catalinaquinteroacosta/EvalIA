"""Whole-package reread with literal normative context, without assigning notes."""
import argparse
from collections import Counter
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from crisis_semantic.closure_run import OUT,read,write,context
from crisis_semantic.domain import load_contracts,package_codes,digest
from crisis_semantic.span_provider import SpanProvider
from crisis_semantic.pipeline import CrisisEvaluator

class LiteralContractProvider(SpanProvider):
    def run(self,stage,system,content,schema,ids,identity,**kwargs):
        codes={v['code'] for k,v in content['predicates'].items() if not self.seed.get(k) or self.seed[k]['value'] is None}
        if 'CR-RI3' in codes:codes.add('CR-RI2')
        contracts,_,_=load_contracts()
        supplement={c:contracts[c] for c in codes}
        # The API observes components. Official levels are supplied only as
        # normative context; neither requested schema nor output contains scores.
        content={**content,'official_literal_contracts':supplement,
                 'documentary_review':'Comprueba todos los componentes del foco. Reconocer hechos no acredita por si solo distinguirlos de interpretaciones o temores. Una omision no acredita por si sola realizar una conducta contraria. No inventes material ausente ni frases obligatorias. No asignes niveles ni puntuaciones.'}
        return super().run(stage,system,content,schema,ids,{**identity,'literal_contract_review':digest(supplement),'review_version':1},**kwargs)

def run(allow_api=False):
    path=OUT/'conversation_api_attempt.json';data=read(path);contracts,_,_=load_contracts()
    provider=LiteralContractProvider(allow_api=allow_api);before=provider.store.summary()
    write(OUT/'conversation_before_literal_review.json',data)
    for batch in data['reports']:
        unresolved=[r for r in batch['evaluation']['results'] if r['status']=='BLOCKED' and not str(r['technical_cause']).startswith('api_transport')]
        if not unresolved:continue
        reread={r['code'] for r in unresolved if r['technical_cause']=='official_anchor_boundary_pending'}
        provider.seed={k:v for r in batch['evaluation']['results'] if r['code'] not in reread for k,v in r.get('verified_decisions',{}).items()}
        provider.reusable_regressions={'CR-RI2','CR-CE10'}
        print('LITERAL CONTRACT PACKAGE',batch['context']['current_turn'],batch['package'],[r['code'] for r in unresolved],flush=True)
        batch['evaluation']=CrisisEvaluator(provider).evaluate(context(batch['context']),package_codes(contracts,batch['package']))
    after=provider.store.summary();rows=[r for b in data['reports'] for r in b['evaluation']['results']]
    data.update(statuses=dict(Counter(r['status'] for r in rows)),blocked_causes=dict(Counter(r['technical_cause'] for r in rows if r['status']=='BLOCKED')),complete=all(r['status']!='BLOCKED' for r in rows),usage=after,
                api_attempts_added=data['api_attempts_added']+after['calls']-before['calls'],cost_added_usd=data['cost_added_usd']+after['estimated_cost_usd']-before['estimated_cost_usd'])
    write(path,data);print(data['statuses'],data['blocked_causes'])

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--allow-api',action='store_true');run(parser.parse_args().allow_api)
