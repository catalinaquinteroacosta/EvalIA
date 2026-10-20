"""Offline documentary matrix and canonical 072 preparation; no API capability."""
from pathlib import Path
from hashlib import sha256
from collections import Counter
import inspect
import json
from .official_contracts import read_contracts
from .identified_context import OriginalTurn, authorized_context
from . import component_routes as routes, em_component_adapter as em
from .result_tables import export_new, grouped
from .budgeted_reader import estimate

def write_new(path,value):
    with path.open('x',encoding='utf-8') as out:json.dump(value,out,ensure_ascii=False,indent=2)

def prepare(root,directory):
    root=Path(root).resolve();directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    rubric=root/'PUNTAJES EVALUADORES ANSIEDAD(20261008-000023).docx'
    official=read_contracts(rubric)
    matrix=[]
    for code,contract in official['contracts'].items():
        module=em if code.startswith('EM') else routes.route(code)
        source=Path(inspect.getfile(module))
        definitions=em.COMPONENT_DESCRIPTIONS[code] if code.startswith('EM') else routes.definitions(code)
        exceptions=[]
        if code in ('EM6','EM13','ND1'):exceptions.append('Adjudicación humana expresa de 2026-10-12; no transferencia entre indicadores.')
        if code=='PS9':exceptions.append('Combinaciones sin anclaje inequívoco permanecen BLOCKED; no traslado de CRISIS.')
        if code=='PS5':exceptions.append('Recurso concreto requiere comprobación factual externa; acuerdo semántico no basta.')
        matrix.append({**contract,'components':definitions,
            'deterministic_module':str(source.relative_to(root)).replace('\\','/'),
            'deterministic_source_sha256':sha256(source.read_bytes()).hexdigest(),
            'deterministic_source_literal':source.read_text(encoding='utf-8'),
            'contract_fault_tests':'tests/ansiedad_semantic/test_all81_fail_closed.py',
            'family_regressions':[str(p.relative_to(root)).replace('\\','/') for p in (root/'tests/ansiedad_semantic').glob('test_*.py')
                if code[:2].lower() in p.stem or p.stem in ('test_component_family_routes','test_integral_engine','test_functional_and_guardrail_routes')],
            'differences_and_adjudications':exceptions,
            'implemented':True,'local_contract_tested':True,'live_semantics_of_this_route_validated':False,
            'clinical_validation':False})
    write_new(directory/'fidelity_matrix.json',{'source_sha256':official['source_sha256'],
        'indicators':matrix,'counts':dict(Counter(r['family'] for r in matrix)),
        'qualification':'Trazabilidad documental y código; no constituye por sí sola validación semántica.'})
    dataset=root/'backend/evaluators/semantic/em/reports/experiment72_dataset.json'
    data=json.loads(dataset.read_text(encoding='utf-8-sig'))
    originals=[OriginalTurn('experiment072',r['model'],r['turn'],r['user_message'],r['ai_response']) for r in data]
    tasks=[];requests=[]
    for original in originals:
        identified=authorized_context(originals,original.conversation,original.model,original.turn)
        for code,contract in official['contracts'].items():
            tasks.append({'conversation':original.conversation,'model':original.model,'turn':original.turn,
                'code':code,'family':contract['family'],'input_sha256':identified['input_sha256'],
                'status':'PENDING','score':None,'applicability':'NOT_YET_VERIFIED',
                'reason':'Preparado; no se ha ejecutado la evaluación semántica de esta ruta.'})
        def collector(request):
            requests.append(request)
            return {}  # deliberately invalid; returned decisions are discarded
        for family in ('AF','GD','PS','PA','ND','CP','IR','EM','CE'):
            if family=='EM':em.run_family(identified,reader=collector)
            else:routes.run_family(identified,family,reader=collector)
    assert len(tasks)==2025 and len(requests)==450
    export_new(directory/'experiment072_pending',tasks)
    write_new(directory/'experiment072_groups.json',{name:grouped(tasks,fields) for name,fields in
        {'indicator':('code',),'family':('family',),'model':('model',),'turn':('model','turn'),
         'conversation':('conversation','model')}.items()})
    write_new(directory/'prepared_requests.json',requests)
    costs=[]
    for i,request in enumerate(requests):
        model='gpt-4.1-mini-2025-04-14' if request['stage']=='extract' else 'gpt-4.1-2025-04-14'
        costs.append({'request_index':i,'model':model,'stage':request['stage'],**estimate(request,model)})
    from decimal import Decimal
    write_new(directory/'api_estimate.json',{'api_calls_executed':0,'base_calls':len(costs),
        'base_reservation_upper_bound_usd':str(sum(Decimal(c['reserved_upper_bound_usd']) for c in costs)),
        'requests':costs,'pricing_sources':['https://developers.openai.com/api/docs/models/gpt-4.1-mini',
        'https://developers.openai.com/api/docs/models/gpt-4.1'],
        'qualification':'Reserva conservadora con un token por byte UTF-8 más margen y salida máxima; no gasto real ni saldo de cuenta comprobado.'})
    frozen=json.loads((root/'docs/crisis_semantic/ac9_live8/files.json').read_text(encoding='utf-8-sig'))
    integrity=[{'path':r['path'],'matches_recorded_sha256':sha256((root/r['path']).read_bytes()).hexdigest()==r['sha256']} for r in frozen]
    write_new(directory/'crisis_integrity.json',{'checked':len(integrity),'mismatches':[r for r in integrity if not r['matches_recorded_sha256']],
        'files':integrity,'shared_sqlite_opened':False})
    return {'indicators':len(matrix),'responses':len(originals),'pending_evaluations':len(tasks),'prepared_calls':len(requests),
            'api_calls':0,'crisis_mismatches':sum(not r['matches_recorded_sha256'] for r in integrity)}

if __name__=='__main__':
    import sys
    print(json.dumps(prepare(sys.argv[1],sys.argv[2]),ensure_ascii=False))
