"""Versioned, network-free replay of preserved release rows; never calls readers."""
import copy
import itertools
import json
import socket
import sys
from hashlib import sha256
from pathlib import Path
from . import component_routes as routes, em_component_adapter as em
from .official_contracts import read_contracts
from .result_tables import export_new
from backend.evaluators.nd.contracts import TurnContext, HistoryTurn, Evidence

BASE = Path('docs/ansiedad_semantic/closure6_20261013/integral_live')
FROZEN = BASE/'release_01'

def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))

def digest(p):
    return sha256(Path(p).read_bytes()).hexdigest()

def save(p,value):
    with Path(p).open('x',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2)

def recover_pair(row):
    code=row['code']; source=Path(row['evidence_source']); d=read(source)
    if 'extraction' in row:
        return row['extraction'],row.get('independent_verification',row.get('verification')),[str(source)]
    if row['validation_scope'] in ('integration','experiment072_ChatGPT_1'):
        f=d['families'][row['family']]
        if code=='CE10' and row['turn']==1 and not row['original']['prior_history']:
            return None,None,[str(source)]
        return f['extraction']['indicators'][code],f['independent_verification']['indicators'][code],[str(source)]
    if row['validation_scope']=='reused_PA8_contrast':
        return d['extraction']['indicators'][code],d['independent_verification']['indicators'][code],[str(source)]
    paths=list(source.parent.glob('*.json'))
    extras={
        'PA1':['../live_5A_02/critical-PA1_extract.json'],
        'IR2':['../continue_5A_IR2/extract.json'],
        'PA3':['critical-PA3_02/independent_verify.json'],
    }
    paths += [BASE/p for p in extras.get(code,[])]
    if row['validation_scope']=='reused_conditional_and_AF4_contexts':
        for s in read(BASE/'prior_context_supplement_03/sources.json'):
            if s['code']==code and s.get('case')==row.get('case'):
                paths.append(Path(s['path']))
    candidates=[]
    for path in paths:
        if not path.exists():continue
        item=read(path)
        if not isinstance(item,dict):continue
        case=item.get('case',{})
        original=item.get('original') or item.get('request',{}).get('original') or (case.get('original') if isinstance(case,dict) else None)
        if original and original.get('input_sha256')!=row['input_sha256']:continue
        stage=item.get('request',{}).get('stage')
        if stage is None:
            stage='independent_verify' if 'verif' in path.name else 'extract' if 'extract' in path.name else None
        def collect(obj,role=stage):
            if not isinstance(obj,dict):return
            if 'indicators' in obj and isinstance(obj['indicators'],dict) and code in obj['indicators'] and isinstance(obj['indicators'][code],dict) and 'components' in obj['indicators'][code] and all(isinstance(v,dict) and 'value' in v for v in obj['indicators'][code]['components'].values()):
                candidates.append((obj['indicators'][code],str(path),role))
            for key in ('reading','extraction','independent_verification','verification'):
                if key in obj:collect(obj[key], 'extract' if key=='extraction' else 'independent_verify' if key in ('independent_verification','verification') else role)
        collect(item)
    # Select by exact saved component facts, reasons and ordered citations,
    # never by agreement with a target score. No synthetic reader is created.
    reviews=row.get('reviews',[])
    def matches(a,b):
        for r in reviews:
            x=a.get('components',{}).get(r['name']);y=b.get('components',{}).get(r['name'])
            if x is None or y is None:return False
            if x['value']!=r['extracted'] or y['value']!=r['verified']:return False
            if x['reason']+' | '+y['reason']!=r['reason']:return False
            if x['evidence']+y['evidence']!=r['evidence']:return False
            if x['counterevidence']+y['counterevidence']!=r['counterevidence']:return False
        return bool(reviews)
    for (a,pa,sa),(b,pb,sb) in itertools.product(candidates,repeat=2):
        if sa=='extract' and sb=='independent_verify' and matches(a,b):return a,b,[pa,pb]
    raise ValueError('Original independent pair not recovered: '+code+' '+str(source))

def run(version):
    def forbidden(*a,**k):raise RuntimeError('Offline replay: network prohibited')
    socket.create_connection=forbidden
    socket.socket.connect=forbidden
    socket.socket.connect_ex=forbidden
    out=BASE/('ratification_'+version);out.mkdir(exist_ok=False)
    old=read(FROZEN/'tables/observations.json');new=[];trace=[];changes=[];literal_errors=[]
    original_files={str(p):digest(p) for p in FROZEN.rglob('*') if p.is_file()}
    for index,row in enumerate(old):
        o=row['original'];ctx=TurnContext(o['user'],o['response'],tuple(HistoryTurn(**h) for h in o['prior_history']))
        sources=[]
        try:
            a,b,sources=recover_pair(row)
            if a is None:
                if not (row['code']=='CE10' and o['turn']==1 and not o['prior_history']):raise ValueError('Invalid fixed gate')
                decision={'code':'CE10','status':'N/A','score':None,'reason':row['reason']}
            else:
                decision=em.adjudicate(row['code'],ctx,a,b) if row['family']=='EM' else routes.adjudicate(row['code'],ctx,a,b)
            current={**copy.deepcopy(row),**decision}
        except (KeyError,ValueError,TypeError) as error:
            current={**copy.deepcopy(row),'status':'BLOCKED','score':None,'reason':str(error)}
        current['applicability']='APPLICABLE' if current['status']=='SCORED' else 'NOT_APPLICABLE' if current['status']=='N/A' else 'UNRESOLVED'
        current['gate_reason']=current['reason'] if current['status']=='N/A' else ''
        new.append(current)
        trace.append({'row':index,'code':row['code'],'sources':[{'path':p,'sha256':digest(p)} for p in sources]})
        if (row['status'],row['score'])!=(current['status'],current['score']):
            changes.append({'row':index,'code':row['code'],'scope':row['validation_scope'],'before':[row['status'],row['score']],
                            'after':[current['status'],current['score']],'reason':current['reason']})
        def audit(value):
            if isinstance(value,dict):
                if 'source' in value and 'quote' in value:
                    if not Evidence(value['source'],value['quote'],value.get('history_index')).verify_exact(ctx):literal_errors.append({'row':index,'citation':value})
                for v in value.values():audit(v)
            elif isinstance(value,list):
                for v in value:audit(v)
        audit({k:v for k,v in current.items() if k!='original'})
    export_new(out/'tables',new)
    save(out/'comparison.json',{'rows':len(new),'changes':changes,'literal_errors':literal_errors,'paid_calls':0})
    save(out/'evidence_trace.json',trace)
    normative=read_contracts('PUNTAJES EVALUADORES ANSIEDAD(20261008-000023).docx')
    matrix=[]
    for code,c in normative['contracts'].items():
        rr=[r for r in new if r['code']==code]
        module=em if c['family']=='EM' else routes.route(code)
        matrix.append({**c,'scorer_module':module.__name__,'observed_states':sorted(set(r['status'] for r in rr)),
                       'observed_levels':sorted(set(r['score'] for r in rr if r['status']=='SCORED')),
                       'rows':len(rr),'semantic_generalization_certified':False})
    save(out/'fidelity_matrix_81.json',matrix)
    assert all(digest(p)==h for p,h in original_files.items()),'Frozen evidence changed'
    save(out/'historical_integrity.json',original_files)
    print(json.dumps({'destination':str(out),'rows':len(new),'changes':changes,'literal_errors':len(literal_errors)},ensure_ascii=True))

if __name__=='__main__':run(sys.argv[1])
