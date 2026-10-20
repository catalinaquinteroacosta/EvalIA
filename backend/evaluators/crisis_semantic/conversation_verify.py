"""Offline integrity audit of every result in the complete API conversation."""
from collections import Counter
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from crisis_semantic.closure_run import OUT,read,write,context
from crisis_semantic.domain import load_contracts,package_codes
from crisis_semantic.scoring import resolve_score
from crisis_semantic.evidence import literal_check
from crisis_semantic.predicate_catalog import definitions
from crisis_semantic.research_tables import export

def run():
    trial=read(OUT/'conversation_api_attempt.json');contracts,_,_=load_contracts()
    errors=[];pending=[];checked=0
    for batch in trial['reports']:
        ctx=context(batch['context']);rows=batch['evaluation']['results']
        assert {r['code'] for r in rows}==set(package_codes(contracts,batch['package']))
        assert all(t.number<ctx.current.number and t.model==ctx.current.model for t in ctx.history)
        for row in rows:
            checked+=1
            if row['status']=='SCORED':
                score,cause=resolve_score(row['code'],{k.split('.',1)[1]:v['value'] for k,v in row['verified_decisions'].items()},contracts)
                if cause or score!=row['score'] or row['official_descriptor']!=contracts[row['code']]['levels'][str(score)]['text']:
                    errors.append({'turn':ctx.current.number,'code':row['code'],'cause':'score_descriptor_mismatch'})
                defs=definitions(contracts,[row['code']])
                for key,decision in row['verified_decisions'].items():
                    if decision['value'] is None:continue
                    for stage in ('extraction','verification'):
                        issues=literal_check(decision[stage],defs[key],ctx,True,batch.get('external_attestations',()))
                        if issues:errors.append({'turn':ctx.current.number,'code':row['code'],'component':key,'cause':issues})
            elif row['score'] is not None:errors.append({'turn':ctx.current.number,'code':row['code'],'cause':'non_numeric_state_has_score'})
            if row['status']=='N/A':
                if contracts[row['code']]['applicability']['kind']=='general':
                    errors.append({'turn':ctx.current.number,'code':row['code'],'cause':'general_indicator_na'})
                elif row['code']=='CR-CE10':
                    if len(ctx.history)>=2:errors.append({'turn':ctx.current.number,'code':row['code'],'cause':'longitudinal_gate_present'})
                else:
                    gate=row.get('verified_decisions',{}).get(row['code']+'.gate',{})
                    if gate.get('value') is not False:errors.append({'turn':ctx.current.number,'code':row['code'],'cause':'na_gate_not_verified_absent'})
            if row['status']=='BLOCKED':pending.append({'turn':ctx.current.number,'package':batch['package'],'code':row['code'],'cause':row['technical_cause'],'decisions':row.get('verified_decisions',{})})
    export(trial['reports'],contracts,OUT/'conversation_tables')
    result={'checked':checked,'statuses':trial['statuses'],'local_errors':errors,'blocked_causes':dict(Counter(p['cause'] for p in pending)),'pending':pending,'clinical_validation':False,'independent_descriptor_audit_included':False}
    write(OUT/'conversation_validation.json',result)
    print({k:v for k,v in result.items() if k!='pending'})
    assert not errors
    return result

if __name__=='__main__':run()
