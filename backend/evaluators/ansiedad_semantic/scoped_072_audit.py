"""Reuse the existing ChatGPT/1 072 audit scope; no paid provider or mass replay."""
from pathlib import Path
from hashlib import sha256
import json,sys
from .closure_integral_live import LIVE,read,save
from .identified_context import OriginalTurn,authorized_context
from . import component_routes as routes,em_component_adapter as em
from .result_tables import aggregate,export_new
from backend.evaluators.nd.contracts import TurnContext,HistoryTurn

BASE=Path('docs/ansiedad_semantic/live_990_20261012')
ROWS=BASE/'night_consolidated_05/tables/observations.json'
IR6=BASE/'targeted_5/7cccdfd44f24b3c6efb9c9a70a4d3e7c85c16fbb93f5c10cd7eea908c267fe1f_IR6.json'

def get_scope():
    data=json.loads(Path('backend/evaluators/semantic/em/reports/experiment72_dataset.json').read_text(encoding='utf-8-sig'))
    originals=[OriginalTurn('experiment072',r['model'],r['turn'],r['user_message'],r['ai_response']) for r in data]
    original=authorized_context(originals,'experiment072','ChatGPT',1)
    rows=[r for r in read(ROWS) if (r['model'],r['turn'])==('ChatGPT',1)]
    assert len(rows)==81
    return original,rows

def paired(row):
    a=row.get('extraction');b=row.get('independent_verification',row.get('verification'))
    if a and b:return a,b,ROWS
    if row.get('paired_private_artifacts'):
        from .step5a_continue import events
        settled={e['artifact']:e for e in events() if e['kind']=='settled' and e.get('valid_output')}
        pair={}
        for path in row['paired_private_artifacts']:
            p=Path(path);event=settled[p.name]
            if sha256(p.read_bytes()).hexdigest()!=event['artifact_sha256']:raise ValueError('Private pair hash mismatch')
            packet=read(p)
            if packet['request']['original']['input_sha256']!=row['input_sha256']:raise ValueError('Private pair original mismatch')
            pair[packet['request']['stage']]=packet['reading']['indicators'][row['code']]
        return pair['extract'],pair['independent_verify'],ROWS
    p=Path(row['paired_source_recovered']) if row.get('paired_source_recovered') else IR6 if row['code']=='IR6' else None
    if p is None:raise ValueError('No actual paired source: '+row['code'])
    d=read(p);c=row['code']
    if 'extraction' not in d:
        from .step5a_continue import events
        from .budgeted_reader import ROOT,canonical
        pairs={}
        for e in events():
            if e['kind']!='settled' or not e.get('valid_output'):continue
            artifact=ROOT/e['artifact'];raw=artifact.read_bytes()
            if sha256(raw).hexdigest()!=e['artifact_sha256']:raise ValueError('Historical artifact hash mismatch')
            packet=json.loads(raw);q=packet['request']
            if q.get('original',{}).get('input_sha256')!=row['input_sha256'] or c not in q.get('indicators',{}):continue
            key=canonical({'original':q['original'],'indicators':q['indicators']})
            pairs.setdefault(key,{})[q['stage']]={'reading':packet['reading'],'path':artifact,'attempt':e['attempt']}
        complete=[p for p in pairs.values() if 'extract' in p and 'independent_verify' in p]
        if not complete:raise ValueError('Actual historical pair missing for '+c)
        pair=max(complete,key=lambda p:max(x['attempt'] for x in p.values()))
        row['paired_private_artifacts']=[str(pair[s]['path']) for s in ['extract','independent_verify']]
        return pair['extract']['reading']['indicators'][c],pair['independent_verify']['reading']['indicators'][c],pair['extract']['path']
    return d['extraction']['indicators'][c],d['independent_verification']['indicators'][c],p

def run(version):
    out=LIVE/('scope072_'+version);out.mkdir(exist_ok=False)
    o,rows=get_scope();ctx=TurnContext(o['user'],o['response'],tuple(HistoryTurn(**h) for h in o['prior_history']))
    updates=[];changes=[];sources=[]
    overrides={'IR6':LIVE/'component_revision_072-IR6-literal_01/adjudication.json',
        'EM9':LIVE/'component_revision_072-EM9-gates_01/adjudication.json'}
    for old in rows:
        c=old['code']
        if c=='CE10' and not o['prior_history']:
            d={k:old[k] for k in ['code','status','score','reason']};p=ROWS
            assert d['status']=='N/A'
        elif c in overrides and overrides[c].exists():d=read(overrides[c])[c];p=overrides[c]
        else:
            a,b,p=paired(old)
            d=em.adjudicate(c,ctx,a,b) if c.startswith('EM') else routes.adjudicate(c,ctx,a,b)
        if (d['status'],d['score'])!=(old['status'],old['score']):
            changes.append({'code':c,'historical':[old['status'],old['score']],'current':[d['status'],d['score']],'reason':d['reason']})
        sources.append({'code':c,'path':str(p),'sha256':sha256(p.read_bytes()).hexdigest(),'private_artifacts':old.get('paired_private_artifacts',[])})
        updates.append({**d,'conversation':o['conversation'],'model':o['model'],'turn':o['turn'],'family':c[:2],
            'input_sha256':o['input_sha256'],'applicability':'APPLICABLE' if d['status']=='SCORED' else 'NOT_APPLICABLE' if d['status']=='N/A' else 'UNRESOLVED',
            'gate_reason':d['reason'] if d['status']=='N/A' else ''})
    save(out/'original.json',o);save(out/'sources.json',sources);save(out/'changes.json',changes)
    export_new(out/'tables',updates)
    save(out/'summary.json',{'scope':'Existing adjudication anchor experiment072 ChatGPT turn1, all81 indicators; other models/turns retain historical partial status. No selection based on target grades.',
        'results':aggregate(updates),'new_API_calls_by_this_offline_audit':0,
        'historical_grades_are_not_gold':True,'mass_2025_repeated':False})
    print(json.dumps({'results':aggregate(updates),'changes':changes},ensure_ascii=False))

if __name__=='__main__':run(sys.argv[1] if len(sys.argv)>1 else '01')
