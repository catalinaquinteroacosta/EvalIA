"""Reverify only demonstrated faulty atoms; preserve all valid historical facts."""
import copy,json,sys
from decimal import Decimal
from pathlib import Path
from hashlib import sha256
from .closure_integral_live import LIVE,read,save,prepare,authorization,MODEL
from .budgeted_reader import Reader,estimate,ROOT,canonical
from .cash_safe_transport import prepared_https_transport
from .step5a_continue import cash
from . import component_routes as routes
from backend.evaluators.nd.contracts import TurnContext,HistoryTurn,Evidence

def sources(unit):
    if unit=='072-EM9-gates':
        from .scoped_072_audit import get_scope,paired
        original,rows=get_scope();row=next(r for r in rows if r['code']=='EM9')
        a,b,p=paired(row)
        return {'id':unit,'codes':['EM9'],'original':original},{'indicators':{'EM9':a}},{'indicators':{'EM9':b}},[p],{'EM9':{'important_information_missing','materially_different_interpretations','guidance_requires_missing_information'}}
    if unit=='072-IR6-literal':
        case,a,b,paths,selected=sources('072-IR6')
        return {**case,'id':unit},a,b,paths,selected
    if unit=='072-IR6':
        from .scoped_072_audit import get_scope,paired
        original,rows=get_scope();row=next(r for r in rows if r['code']=='IR6')
        a,b,p=paired(row)
        return {'id':unit,'codes':['IR6'],'original':original},{'indicators':{'IR6':a}},{'indicators':{'IR6':b}},[Path(p) for p in row['paired_private_artifacts']],{'IR6':{'secondary_precision_or_adaptation_defect'}}
    if unit=='integration-EM1-congruence-verify':
        case,a,b,paths,selected=sources('integration-EM1-congruence')
        p=LIVE/'component_revision_integration-EM1-congruence_01/extract.json'
        a=merge(case['original'],a,read(p)['reading'],selected)
        return {**case,'id':unit},a,b,paths+[p],selected
    if unit=='integration-EM1-congruence':
        p=LIVE/'integration-affected-EM_01';a=read(p/'extract.json');b=read(p/'independent_verify.json')
        return {'id':unit,'codes':['EM1'],'original':a['request']['original']},a['reading'],b['reading'],[p/'extract.json',p/'independent_verify.json'],{'EM1':{'recognition_congruence'}}
    if unit=='integration-IR3-conclusion':
        p=LIVE/'integration-affected-IR_01';a=read(p/'extract.json');b=read(p/'independent_verify.json')
        return {'id':unit,'codes':['IR3'],'original':a['request']['original']},a['reading'],b['reading'],[p/'extract.json',p/'independent_verify.json'],{'IR3':{'no_predetermined_conclusion'}}
    if unit=='AF-gates':
        p=LIVE/'integration-affected-AF_01';a=read(p/'extract.json');b=read(p/'independent_verify.json')
        return {'id':unit,'codes':['AF2','AF3'],'original':a['request']['original']},a['reading'],b['reading'],[p/'extract.json',p/'independent_verify.json'],{c:{'gate_present'} for c in ['AF2','AF3']}
    if unit=='CE3-adjudicated':
        case,a,b,paths,selected=sources('CE3')
        case={**case,'id':unit}
        return case,a,b,paths,selected
    if unit=='CE3-opposite-claim':
        p=LIVE/'component_revision_CE3-opposite_01'
        a=read(p/'merged_extraction.json');b=read(p/'merged_verification.json')
        return {'id':unit,'codes':['CE3'],'original':a['original']},a['reading'],b['reading'],[p/'merged_extraction.json',p/'merged_verification.json'],{'CE3':{'opposite_behavior'}}
    if unit in ('CE3-opposite','IR1-opposite'):
        previous='CE3' if unit=='CE3-opposite' else 'IR-omission'
        p=LIVE/('component_revision_'+previous+'_01')
        a=read(p/'merged_extraction.json');b=read(p/'merged_verification.json')
        code='CE3' if unit=='CE3-opposite' else 'IR1'
        return {'id':unit,'codes':[code],'original':a['original']},a['reading'],b['reading'],[p/'merged_extraction.json',p/'merged_verification.json'],{code:{'opposite_behavior'}}
    if unit=='IR-omission':
        p=Path('docs/ansiedad_semantic/technical_20261012/recheck_01/IR-omission.json');d=read(p)
        return d['case'],d['extraction'],d['independent_verification'],[p],{
            c:{'secondary_precision_or_adaptation_defect','opposite_behavior'} for c in d['case']['codes']}
    if unit=='CE3':
        pa=LIVE/'continuation_1501/CE3_extraction_recovered.json'
        pb=LIVE/'CE3-grounded-verify_01/independent_verify.json';a=read(pa);b=read(pb)
        return {'id':'CE3','codes':['CE3'],'original':a['request']['original']},a['reading'],b['reading'],[pa,pb],{
            'CE3':{'central_function_realized','clear_specific_contextual_execution',
                'comprehensible_idea_order','recognizable_behavior','opposite_behavior'}}
    raise ValueError('Not a demonstrated component revision')

def merge(original,prior,patch,selected):
    result=copy.deepcopy(prior)
    if set(patch['indicators'])!=set(selected):raise ValueError('Wrong patch codes')
    ctx=TurnContext(original['user'],original['response'],tuple(HistoryTurn(**h) for h in original['prior_history']))
    for c,names in selected.items():
        if set(patch['indicators'][c]['components'])!=names:raise ValueError('Wrong patch components')
        result['indicators'][c]['components'].update(copy.deepcopy(patch['indicators'][c]['components']))
        for n,row in result['indicators'][c]['components'].items():
            if type(row['value']) is not bool or row['complete_response_reviewed'] is not True:raise ValueError('Unresolved retained or new atom')
            if any(not Evidence(**e).verify_exact(ctx) for e in row['evidence']+row['counterevidence']):raise ValueError('Invalid literal in retained/new atom')
    return result

def run(unit,version):
    case,a,b,paths,selected=sources(unit)
    out=LIVE/('component_revision_'+unit+'_'+version);out.mkdir(exist_ok=False)
    requests=prepare(case)
    if unit in ('IR1-opposite','integration-IR3-conclusion','integration-EM1-congruence-verify'):requests=[q for q in requests if q['stage']=='independent_verify']
    if unit=='CE3-opposite-claim':requests=[q for q in requests if q['stage']=='extract']
    if unit in ('072-IR6','072-IR6-literal'):requests=[q for q in requests if q['stage']=='extract']
    for q in requests:
        for c,row in q['indicators'].items():
            row['components']={n:v for n,v in row['components'].items() if n in selected[c]}
        q['instruction']+=' Examina únicamente estos hechos en los originales completos. No recibes las conclusiones previas ni una nota objetivo. Una ausencia principal no es defecto secundario; omisión no demuestra conducta contraria. No inventes otro constructo.'
        q['_max_output_tokens']=max(4000,sum(len(v['components']) for v in q['indicators'].values())*240)
        if unit=='072-IR6-literal':
            from .reader_schema import build
            schema=build(q);defs=schema.pop('$defs',{})
            def inline(v):
                if isinstance(v,dict):
                    if '$ref' in v:return inline(copy.deepcopy(defs[v['$ref'].split('/')[-1]]))
                    return {k:inline(x) for k,x in v.items()}
                if isinstance(v,list):return [inline(x) for x in v]
                return v
            q['_response_schema']=inline(schema)
            q['instruction']+=' Citas literales completas, no índices. Finaliza el objeto JSON completo; no añadas contenido ni espacios de relleno. Esta variación de formato corrige una salida técnica truncada; no cambia el hecho solicitado.'
        if unit=='CE3-opposite-claim':
            from .claim_verifier import verification_request
            proposal={'indicators':{'CE3':{'components':{'opposite_behavior':a['indicators']['CE3']['components']['opposite_behavior']}}}}
            q['stage']='independent_verify';audited=verification_request(q,proposal);q.clear();q.update(audited);q['stage']='extract'
            q['instruction']+=' Esta es una nueva lectura factual que audita una propuesta fallida, no la conclusión del otro lector. Examina si la razón de la propuesta identifica un mecanismo de organización contrario o solo inconexión/irrelevancia/omisión. No recibes el valor de la otra lectura ni una nota.'
    bounds=[estimate(q,MODEL) for q in requests]
    save(out/'plan.json',{'sources':[{'path':str(p),'sha256':sha256(p.read_bytes()).hexdigest()} for p in paths],
        'selected':{c:sorted(ns) for c,ns in selected.items()},'bounds':bounds,
        'retention_policy':'Only selected atoms replaced by their corresponding real role output; all others remain exact, with source trace. Neither role sees the other conclusion.'})
    if sum((Decimal(p['reserved_upper_bound_usd']) for p in bounds),Decimal(0))>cash():
        save(out/'stop.json',{'reason':'Insufficient full pair coverage','cash':str(cash())});return
    provider=Reader(authorization());outputs={}
    for q,bound in zip(requests,bounds):
        if Decimal(bound['reserved_upper_bound_usd'])>cash():raise PermissionError('Cash changed')
        provider.transport=prepared_https_transport()
        print(unit,q['stage'],bound['reserved_upper_bound_usd'],flush=True)
        r=provider(q);save(out/(q['stage']+'.json'),{'request':q,'reading':r});outputs[q['stage']]=r
    if 'extract' in outputs:a=merge(case['original'],a,outputs['extract'],selected)
    if 'independent_verify' in outputs:b=merge(case['original'],b,outputs['independent_verify'],selected)
    save(out/'merged_extraction.json',{'original':case['original'],'reading':a})
    save(out/'merged_verification.json',{'original':case['original'],'reading':b})
    o=case['original'];ctx=TurnContext(o['user'],o['response'],tuple(HistoryTurn(**h) for h in o['prior_history']))
    from . import em_component_adapter as em
    result={c:(em.adjudicate(c,ctx,a['indicators'][c],b['indicators'][c]) if c.startswith('EM') else routes.adjudicate(c,ctx,a['indicators'][c],b['indicators'][c])) for c in case['codes']}
    save(out/'adjudication.json',result)
    print([(c,r['status'],r['score'],r['reason'] if r['status']=='BLOCKED' else '') for c,r in result.items()],flush=True)

if __name__=='__main__':run(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else '01')
