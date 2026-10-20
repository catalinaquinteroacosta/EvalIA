"""Reuse validated active conditional contexts and AF4 levels, without API."""
from pathlib import Path
from hashlib import sha256
import sys,json,re
from .closure_integral_live import LIVE,read,save
from . import component_routes as routes,em_component_adapter as em
from .result_tables import aggregate,export_new
from backend.evaluators.nd.contracts import TurnContext,HistoryTurn

def run(version):
    out=LIVE/('prior_context_supplement_'+version);out.mkdir(exist_ok=False)
    baseline=read('docs/ansiedad_semantic/finish_20261013/final_02/tables/observations.json')
    requested=[('AF4','AF4-level-'+str(i)) for i in range(4)]
    requested += [(c,case) for c in ['PS2','PS3','PS5','PS9','PS10'] for case in ['PS-full','PS-omission']]
    requested += [('EM9','EM-full'),('EM9','EM-omission'),('PS6','PS-full'),('GD7','GD-full')]
    rows=[];sources=[]
    if version!='01':
        from backend.evaluators.nd.docx_components import contracts
        previous=LIVE/'prior_context_supplement_01'
        rows=read(previous/'tables/observations.json');sources=read(previous/'sources.json')
        anchors=[]
        for name in ['integration','experiment072_ChatGPT_1']:
            anchors+=read(LIVE/'final_engine_replay_02'/name/'tables/observations.json')
        requested=[]
        for c,d in contracts().items():
            if not re.match(r'^(?:Aplicabilidad:\s*)?CONDICIONAL\b',d['applicability_literal'],re.I):continue
            if any(r['code']==c and r['status']=='N/A' for r in anchors+rows):continue
            candidates=[r for r in baseline if r['code']==c and r['status']=='N/A' and r['case'].endswith('inactive')]
            if not candidates:raise ValueError('No reused inactive gate evidence for '+c)
            requested.append((c,candidates[0]['case']))
    for code,case in requested:
        old=next(r for r in baseline if r['code']==code and r['case']==case)
        path=Path(old['source']);d=read(path);o=d['case']['original']
        ctx=TurnContext(o['user'],o['response'],tuple(HistoryTurn(**h) for h in o['prior_history']))
        a=d['extraction']['indicators'][code];b=d['independent_verification']['indicators'][code]
        result=em.adjudicate(code,ctx,a,b) if code.startswith('EM') else routes.adjudicate(code,ctx,a,b)
        rows.append({**result,'conversation':o['conversation'],'model':o['model'],'turn':o['turn'],'family':code[:2],
            'input_sha256':o['input_sha256'],'applicability':'APPLICABLE' if result['status']=='SCORED' else 'NOT_APPLICABLE' if result['status']=='N/A' else 'UNRESOLVED',
            'gate_reason':result['reason'] if result['status']=='N/A' else '',
            'case':case,'evidence_source':str(path),'original':o})
        sources.append({'code':code,'case':case,'path':str(path),'sha256':sha256(path.read_bytes()).hexdigest(),
            'historical':[old['status'],old['score']],'current':[result['status'],result['score']]})
    export_new(out/'tables',rows);save(out/'sources.json',sources)
    save(out/'summary.json',{'results':aggregate(rows),'new_API_calls':0,
        'purpose':'Reuse already validated active conditional gates and real AF4 four-level contrasts, not simulated components or new gold labels.'})
    print(json.dumps({'results':aggregate(rows),'blocked':[(r['code'],r['case'],r['reason']) for r in rows if r['status']=='BLOCKED']}))

if __name__=='__main__':run(sys.argv[1] if len(sys.argv)>1 else '01')
