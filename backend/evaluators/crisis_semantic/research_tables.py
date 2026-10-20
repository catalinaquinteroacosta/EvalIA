"""Isolated research exports. Missing/blocked observations never become zero."""
from collections import Counter
import csv
import io
import json

def aggregate(rows, expected_count=None, *, percentage_method_confirmed=False):
    if expected_count is not None and (type(expected_count) is not int or expected_count<0 or len(rows)>expected_count):raise ValueError('invalid_or_exceeded_expected_inventory')
    if any(r['status'] not in ('SCORED','N/A','BLOCKED') for r in rows):
        raise ValueError('invalid_status')
    for row in rows:
        if row['status'] == 'SCORED':
            if type(row['score']) is not int or not 0 <= row['score'] <= 3: raise ValueError('invalid_score')
        elif row['score'] is not None: raise ValueError('non_score_state_has_score')
    counts=Counter(r['status'] for r in rows)
    scored=[r['score'] for r in rows if r['status']=='SCORED']
    missing = max(0,expected_count-len(rows)) if expected_count is not None else 0
    validation_pending = sum(bool(r.get('validation_pending')) for r in rows)
    complete = not counts['BLOCKED'] and not missing and not validation_pending
    numerator=sum(scored)
    denominator=len(scored)*3
    candidate = numerator/denominator*100 if complete and denominator else None
    return {'scored':counts['SCORED'],'na':counts['N/A'],'blocked':counts['BLOCKED'],'missing':missing,'validation_pending':validation_pending,'distribution':{str(n):scored.count(n) for n in range(4)},'sum_observed_scores':numerator,'denominator':denominator if complete else None,'technical_complete':complete,'candidate_percentage':candidate,'percentage':candidate if percentage_method_confirmed else None,'percentage_method_confirmed':percentage_method_confirmed,'research_publishable':complete and percentage_method_confirmed,'pending_cause':'blocked_missing_or_validation_pending' if not complete else 'percentage_method_unconfirmed' if not percentage_method_confirmed else None}

def export(reports,contracts,folder,*,percentage_method_confirmed=True):
    rows=[]
    for report in reports:
        for result in report['evaluation']['results']:
            rows.append({'id':f"{report['context']['model_evaluated']}:{report['case']}:{report['context']['current_turn']}:{result['code']}",'case':report['case'],'model':report['context']['model_evaluated'],'turn':report['context']['current_turn'],'family':contracts[result['code']]['family_code'],'code':result['code'],'status':result['status'],'score':result['score'],'evidence':result.get('verified_decisions',{}),'descriptor':result.get('official_descriptor'),'cause':result.get('technical_cause'),'synthetic':True,'validation_pending':result['code'] in report.get('validation_pending_codes',[])})
    if len({r['id'] for r in rows})!=len(rows):raise ValueError('duplicate_observation_identity')
    case_family=[]
    for case,model,turn in sorted({(r['case'],r['model'],r['turn']) for r in rows}):
        for family in sorted({c['family_code'] for c in contracts.values()}):
            selected=[r for r in rows if (r['case'],r['model'],r['turn'],r['family']) == (case,model,turn,family)]
            case_family.append({'case':case,'model':model,'turn':turn,'family':family,**aggregate(selected,sum(c['family_code']==family for c in contracts.values()),percentage_method_confirmed=percentage_method_confirmed)})
    model_family=[]
    cases=len({(r['case'],r['model'],r['turn']) for r in rows})
    for model in sorted({r['model'] for r in rows}):
        for family in sorted({c['family_code'] for c in contracts.values()}):
            selected=[r for r in rows if (r['model'],r['family'])==(model,family)]
            model_cases=len({(r['case'],r['turn']) for r in rows if r['model']==model})
            model_family.append({'model':model,'family':family,**aggregate(selected,model_cases*sum(c['family_code']==family for c in contracts.values()),percentage_method_confirmed=percentage_method_confirmed)})
    indicator=[{'code':code,**aggregate([r for r in rows if r['code']==code],cases,percentage_method_confirmed=percentage_method_confirmed)} for code in contracts]
    additional={}
    for name,keys in [('by_turn',('case','model','turn')),('by_conversation',('case','model')),('by_model',('model',))]:
        records=[]
        for identity in sorted({tuple(r[k] for k in keys) for r in rows}):
            selected=[r for r in rows if tuple(r[k] for k in keys)==identity]
            units=len({(r['case'],r['model'],r['turn']) for r in selected})
            records.append({**dict(zip(keys,identity)),**aggregate(selected,units*len(contracts),percentage_method_confirmed=percentage_method_confirmed)})
        additional[name]=records
    for record in case_family+model_family+indicator+[r for records in additional.values() for r in records]:record['research_publishable']=False
    bundle={'observations':rows,'by_case_family':case_family,'by_model_family':model_family,'by_indicator':indicator,**additional,'synthetic':True,'clinical_validation':False,'percentage_method_status':'Approved user formula: sum(scores)/(applicable_count*3)*100; NA excluded; pending validation blocks complete percentages. Synthetic fixtures are not empirical research data.'}
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'tables.json').write_text(json.dumps(bundle,ensure_ascii=False,indent=2),encoding='utf-8')
    for name,records in [('observations',rows),('by_case_family',case_family),('by_model_family',model_family),('by_indicator',indicator),*additional.items()]:
        stream=io.StringIO(newline='')
        fields=list(records[0])
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for row in records:writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else '' if v is None else v for k,v in row.items()})
        text=stream.getvalue()
        decoded=list(csv.DictReader(io.StringIO(text)))
        assert len(decoded)==len(records)
        for original,roundtrip in zip(records,decoded):
            for key,value in original.items():
                if isinstance(value,(dict,list)): assert json.loads(roundtrip[key])==value
                elif value is None: assert roundtrip[key]==''
                else: assert roundtrip[key]==str(value)
        (folder/(name+'.csv')).write_text(text,encoding='utf-8',newline='')
    return bundle
