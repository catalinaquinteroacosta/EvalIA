"""Immutable synthetic evidence consolidation and deterministic replay; no API."""
from pathlib import Path
from collections import Counter
from hashlib import sha256
import json
from .technical_corpus import cases
from .technical_critical_cases import cases as critical_cases
from .technical_expectations import CORRECTIONS
from .run_authorized_validation import save
from .night_validation import accounting
from . import component_routes as routes, em_component_adapter as em
from backend.evaluators.nd.contracts import TurnContext,HistoryTurn
from backend.evaluators.nd.docx_components import contracts

def run(root,target):
    root=Path(root);target=Path(target);target.mkdir(parents=True,exist_ok=False)
    corpus=cases()+critical_cases();latest={};history=[]
    folders=['live_01','recheck_01','critical_02','critical_recheck_03','requalification_04','requalification_05','requalification_06','causal_07','em_specific_08']
    for folder in folders:
        for file in sorted((root/folder).glob('*.json')):
            packet=json.loads(file.read_text(encoding='utf-8'))
            if not isinstance(packet,dict) or 'decisions' not in packet:continue
            for code,d in packet['decisions'].items():
                a=packet.get('extraction',{});b=packet.get('independent_verification',{})
                x=(a or {}).get('indicators',{}).get(code)
                y=(b or {}).get('indicators',{}).get(code)
                latest[(packet['case']['id'],code)]=(d,x,y,str(file))
    rows=[];replays=[];pending=target/'unresolved_source';pending.mkdir()
    for case in corpus:
        original=case['original'];ctx=TurnContext(original['user'],original['response'],tuple(HistoryTurn(**h) for h in original['prior_history']))
        decisions={}
        for code in case['codes']:
            previous=latest.get((case['id'],code))
            if previous:
                d,x,y,source=previous
                if x is not None and y is not None:
                    d=em.adjudicate(code,ctx,x,y) if code.startswith('EM') else routes.adjudicate(code,ctx,x,y)
                    replays.append({'case':case['id'],'code':code,'before':{k:previous[0][k] for k in ('status','score')},
                        'after':{k:d[k] for k in ('status','score')},'source':source})
                d={**d,'evidence_source':source}
            else:d={'code':code,'status':'PENDING','score':None,'reason':'No completed blind pair'}
            expected,why=CORRECTIONS.get((case['id'],code),(case['expected'].get(code,'UNSPECIFIED'),''))
            match=None if expected=='UNSPECIFIED' else (d['status'],d['score'])==('N/A' if expected is None else 'SCORED',expected)
            rows.append({'case':case['id'],'code':code,'family':code[:2],**{k:d[k] for k in ('status','score','reason')},
                'expected_hypothesis':expected,'hypothesis_matches':match,'fixture_erratum':why,
                'source':d.get('evidence_source'),'qualification':'Agreement is necessary, not sufficient for semantic validity.'})
            decisions[code]=d
        if any(d['status'] in ('BLOCKED','PENDING') for d in decisions.values()) or any(r['case']==case['id'] and r['hypothesis_matches'] is False for r in rows):
            save(pending/(case['id']+'.json'),{'case':case,'decisions':decisions})
    save(target/'observations.json',rows);save(target/'replays.json',replays)
    matrix=[]
    for code,official in contracts().items():
        own=[r for r in rows if r['code']==code]
        module=em if code.startswith('EM') else routes.route(code)
        matrix.append({'code':code,'official':official,'components':em.COMPONENT_DESCRIPTIONS[code] if code.startswith('EM') else routes.definitions(code),
            'route': 'em_component_adapter' if code.startswith('EM') else routes.route(code).__name__,
            'module_path':str(Path(module.__file__)),
            'module_sha256':sha256(Path(module.__file__).read_bytes()).hexdigest(),
            'local_contract_tests':['tests/ansiedad_semantic/test_all81_fail_closed.py','tests/ansiedad_semantic/test_technical_corpus.py'],
            'tested_cases':own,'observed_scored_levels':sorted({r['score'] for r in own if r['status']=='SCORED'}),
            'qualification':'Local tests, implemented route and accepted semantic levels are separate claims.'})
    save(target/'fidelity_matrix.json',matrix)
    counts=Counter(r['status'] for r in rows)
    summary={'scope':'Synthetic motor validation; experiment072 is not a closure prerequisite.',
        'planned_cases':len(corpus),'planned_indicator_cases':len(rows),'indicators':len(matrix),'families':9,
        'counts':dict(counts),'full_percentage':None,'complete':not(counts['BLOCKED'] or counts['PENDING']),
        'accounting':accounting(),'clinical_validation':False,
        'verdict':'NO APTO while semantic discrepancies or coverage requirements remain unresolved.'}
    save(target/'summary.json',summary)
    protected=[]
    for entry in json.loads(Path('docs/crisis_semantic/ac9_live8/files.json').read_text(encoding='utf-8')):
        path=Path(entry['path']);actual=sha256(path.read_bytes()).hexdigest() if path.exists() else None
        protected.append({'path':str(path),'matches':actual==entry['sha256'],'sha256':actual})
    save(target/'integrity.json',{'crisis_manifest_entries':len(protected),
        'crisis_differences':[row for row in protected if not row['matches']],
        'docx_sha256':sha256(Path('PUNTAJES EVALUADORES ANSIEDAD(20261008-000023).docx').read_bytes()).hexdigest(),
        'shared_sqlite_accessed':False,'scope':'Named public CRISIS manifest; not a global Git assertion.'})
    save(target/'source_hashes.json',{str(p):sha256(p.read_bytes()).hexdigest()
        for base in ('backend/evaluators/ansiedad_semantic','backend/evaluators/nd')
        for p in Path(base).glob('*.py')})
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':
    import sys
    run(sys.argv[1],sys.argv[2])
