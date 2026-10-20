"""Offline, non-destructive night evidence consolidation and reproducible audit."""
from pathlib import Path
from hashlib import sha256
from collections import Counter
import json
import csv
import inspect
from .night_validation import BASE, accounting, AUTH, ROOT
from .identified_context import OriginalTurn, authorized_context
from .result_tables import export_new, aggregate, grouped, validate
from . import component_routes as routes, em_component_adapter as em
from .run_authorized_validation import save
from backend.evaluators.nd.contracts import TurnContext, HistoryTurn, Evidence
from backend.evaluators.nd.docx_components import contracts
from backend.evaluators.semantic.em.schemas import COMPONENT_DESCRIPTIONS

def run(directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    source=Path('backend/evaluators/semantic/em/reports/experiment72_dataset.json')
    data=json.loads(source.read_text(encoding='utf-8-sig'))
    originals=[OriginalTurn('experiment072',r['model'],r['turn'],r['user_message'],r['ai_response']) for r in data]
    rows=json.loads((BASE/'night_01/tables/observations.json').read_text(encoding='utf-8'))
    normative=contracts();citations=0;errors=[];replays=[]
    private_pairs={}
    for event in [json.loads(s) for s in (ROOT/'ledger.jsonl').read_text(encoding='utf-8').splitlines()]:
        if event['kind']!='settled' or not event.get('valid_output'):continue
        artifact=ROOT/event['artifact'];raw=artifact.read_bytes()
        if sha256(raw).hexdigest()!=event['artifact_sha256']:raise ValueError('Private settled artifact hash mismatch')
        packet=json.loads(raw);q=packet['request']
        if not q.get('original',{}).get('input_sha256'):continue
        key=json.dumps({'original':q['original'],'indicators':q.get('indicators',{})},sort_keys=True,ensure_ascii=False)
        group=private_pairs.setdefault(key,{})
        group[q['stage']]={'reading':packet['reading'],'artifact':str(artifact),'attempt':event['attempt']}
    def walk(value,context,where):
        nonlocal citations
        if isinstance(value,dict):
            if 'quote' in value and 'source' in value:
                citations+=1
                try:
                    if not Evidence(**{k:value[k] for k in ('source','history_index','quote')}).verify_exact(context):
                        errors.append({'identity':where,'error':'nonliteral_or_unauthorized_citation','citation':value})
                except Exception as error:errors.append({'identity':where,'error':str(error)})
            for item in value.values():walk(item,context,where)
        elif isinstance(value,list):
            for item in value:walk(item,context,where)
    for row in rows:
        validate(row)
        original=authorized_context(originals,row['conversation'],row['model'],row['turn'])
        context=TurnContext(original['user'],original['response'],tuple(HistoryTurn(**h) for h in original['prior_history']))
        identity={k:row[k] for k in ('model','turn','code')}
        if row.get('input_sha256') and row['input_sha256']!=original['input_sha256']:
            errors.append({'identity':identity,'error':'input_hash_mismatch'})
        walk(row,context,identity)
        if row['status'] not in ('SCORED','N/A'):continue
        if row['code']=='CE10' and row['turn']==1 and row['status']=='N/A':
            replays.append({**identity,'matches':True,'basis':'Official first-turn gate; empty authorized prior history.'})
            continue
        a=row.get('extraction');b=row.get('independent_verification',row.get('verification'))
        if not a or not b:
            paths=[Path(row[k]) for k in ('verified_evidence','reused_verified_evidence') if row.get(k)]
            paths+=sorted(BASE.glob('corpus_*/'+original['input_sha256']+'_'+row['family']+'.json'),reverse=True)
            for path in paths:
                if not path.is_file():continue
                saved=json.loads(path.read_text(encoding='utf-8'))
                if not isinstance(saved,dict):continue
                if saved.get('original',{}).get('input_sha256')!=original['input_sha256']:continue
                candidates=saved.get('results',[])
                if isinstance(candidates,list) and candidates and not any(
                    d.get('code')==row['code'] and (d.get('status'),d.get('score'))==(row['status'],row['score']) for d in candidates):continue
                x=saved.get('extraction',{}).get('indicators',{}).get(row['code'])
                y=saved.get('independent_verification',{}).get('indicators',{}).get(row['code'])
                if x and y:
                    a,b=x,y;row['paired_source_recovered']=str(path);break
        if not a or not b:
            candidates=[]
            for key,pair in private_pairs.items():
                q=json.loads(key)
                if q['original']['input_sha256']!=original['input_sha256'] or row['code'] not in q['indicators']:continue
                if 'extract' in pair and 'independent_verify' in pair:
                    candidates.append(pair)
            if candidates:
                pair=max(candidates,key=lambda p:max(v['attempt'] for v in p.values()))
                a=pair['extract']['reading']['indicators'][row['code']]
                b=pair['independent_verify']['reading']['indicators'][row['code']]
                row['paired_private_artifacts']=[v['artifact'] for v in pair.values()]
        if a and b:
            walk(a,context,identity);walk(b,context,identity)
            d=em.adjudicate(row['code'],context,a,b) if row['family']=='EM' else routes.adjudicate(row['code'],context,a,b)
            match=(d['status'],d['score'])==(row['status'],row['score'])
            replays.append({**identity,'before':[row['status'],row['score']],'replay':[d['status'],d['score']],'matches':match,'reason':d['reason']})
            if not match:
                row.update(historical_result={'status':row['status'],'score':row['score']},status='BLOCKED',score=None,
                           applicability='UNRESOLVED',reason='Current deterministic replay differs: '+d['reason'])
        else:errors.append({'identity':identity,'error':'accepted_row_missing_paired_readings'})
    if errors:
        for error in errors:
            error['impedes_adjudication']=True
            row=next(r for r in rows if all(r[k]==v for k,v in error['identity'].items()))
            if row['status']=='N/A' and error['error']=='nonliteral_or_unauthorized_citation':
                a=row.get('extraction',{}).get('components',{}).get('gate_present',{})
                b=row.get('independent_verification',row.get('verification',{})).get('components',{}).get('gate_present',{})
                if a.get('value') is False and b.get('value') is False:
                    gate_text=json.dumps([a,b],ensure_ascii=False)
                    if error['citation']['quote'] not in gate_text:
                        error['impedes_adjudication']=False
                        error['scope']='Invalid unused scoring-component citation; independent inactive official gate remains valid. Preserve defect; do not invent BLOCKED when adjudication does not depend on it.'
        bad={(e['identity']['model'],e['identity']['turn'],e['identity']['code']) for e in errors if e['impedes_adjudication']}
        for row in rows:
            if (row['model'],row['turn'],row['code']) in bad and row['status'] in ('SCORED','N/A'):
                row.update(historical_result={'status':row['status'],'score':row['score']},status='BLOCKED',score=None,
                           applicability='UNRESOLVED',reason='Offline evidence audit failed; see audit_errors.json.')
    export_new(directory/'tables',rows)
    groups={n:grouped(rows,fields) for n,fields in {'family':('family',),'indicator':('code',),'model':('model',),
              'turn':('model','turn'),'conversation':('conversation','model')}.items()}
    save(directory/'groups.json',groups)
    save(directory/'audit_errors.json',errors);save(directory/'deterministic_replays.json',replays)
    save(directory/'na_zero_audit.json',[{**r,'official_gate':normative[r['code']]['applicability_literal'],
         'official_zero':normative[r['code']]['levels']['0']} for r in rows if r['status']=='N/A' or r.get('score')==0])
    save(directory/'blocked_causes.json',dict(Counter(r.get('reason','unspecified') for r in rows if r['status']=='BLOCKED')))
    matrix=json.loads(Path('docs/ansiedad_semantic/integral_20261012/fidelity_matrix_final.json').read_text(encoding='utf-8'))
    for indicator in matrix['indicators']:
        code=indicator['code'];module=em if code.startswith('EM') else routes.route(code)
        indicator.update(components=COMPONENT_DESCRIPTIONS[code] if code.startswith('EM') else routes.definitions(code),
            deterministic_module=module.__name__,deterministic_source_sha256=sha256(Path(module.__file__).read_bytes()).hexdigest(),
            deterministic_source_literal=inspect.getsource(module),
            live_semantics_of_this_route_validated=False,
            live_corpus_status_counts=dict(Counter(r['status'] for r in rows if r['code']==code)),
            qualification='Implementation/local contract tests do not demonstrate complete live validation; inspect per-row evidence.',
            clinical_validation=False)
    matrix['dependent_rules']={str(p):sha256(p.read_bytes()).hexdigest() for p in Path('backend/evaluators/ansiedad_semantic').glob('*.py')}
    matrix['current_adjudications']=[str(BASE/p) for p in ('PS6_GD7_DECISION.md','PA8_DECISION.md')]
    save(directory/'fidelity_matrix.json',matrix)
    protected=[]
    for entry in json.loads(Path('docs/crisis_semantic/ac9_live8/files.json').read_text(encoding='utf-8')):
        path=Path(entry['path']);actual=sha256(path.read_bytes()).hexdigest() if path.exists() else None
        protected.append({'path':str(path),'matches':actual==entry['sha256'],'sha256':actual})
    docx=Path('PUNTAJES EVALUADORES ANSIEDAD(20261008-000023).docx')
    integrity={'crisis_manifest_entries':len(protected),'crisis_differences':[p for p in protected if not p['matches']],
        'docx_sha256':sha256(docx.read_bytes()).hexdigest(),'shared_sqlite_accessed':False,
        'scope':'Public CRISIS manifest hashes only; no global Git claim, no shared cache access.'}
    save(directory/'integrity.json',integrity)
    csvrows=list(csv.DictReader((directory/'tables/observations.csv').open(encoding='utf-8',newline='')))
    assert len(csvrows)==len(rows)==2025
    assert all(a['status']==b['status'] and str(a['score'] if a['score'] is not None else '')==b['score'] for a,b in zip(rows,csvrows))
    summary={'results':aggregate(rows),'family_status':groups['family'],'original_responses':len(originals),
         'models':sorted(set(r.model for r in originals)),'turns':sorted(set(r.turn for r in originals)),
         'literal_citations_checked':citations,'evidence_errors':len(errors),'deterministic_replays':len(replays),
         'replay_mismatches':sum(not r['matches'] for r in replays),'json_csv_roundtrip':True,
         'night_accounting':accounting(),'verdict':'NO APTO','clinical_validation':False}
    save(directory/'summary.json',summary)
    report=['# ANSIEDAD — ejecución nocturna, estado consolidado','',
       'Dictamen: **NO APTO para congelación**. No se completó la validación semántica del Experimento 072. Se conserva todo el historial.',
       '',f"Corpus: {len(originals)} respuestas, cinco modelos, cinco turnos, 81 indicadores y 2.025 combinaciones. Estados: {summary['results']['counts']}. Porcentaje completo: no emitido.",
       '', 'Las nueve familias están implementadas y tienen contratos/pruebas locales. Implementación no equivale a validación semántica completa.',
       '', '| Familia | Indicadores | SCORED | N/A | BLOCKED | PENDING |','|---|---:|---:|---:|---:|---:|']
    from .official_contracts import EXPECTED
    for g in groups['family']:
        c=g['counts'];report.append(f"| {g['family']} | {EXPECTED[g['family']]} | {c['SCORED']} | {c['N/A']} | {c['BLOCKED']} | {c['PENDING']} |")
    report += ['', 'Controles 1–4: cobertura normativa y rutas implementadas; correcciones ND1, EM13, EM6, PS6/GD7 y PA8 registradas. Controles 5–7: pruebas locales aprobadas, corpus/API y auditoría semántica parciales. Control 8: congelación pendiente.',
       '', 'Última batería local completa previa: 3.334 aprobadas, cero fallos actuales (local_final_v3.txt). Se conserva un fallo histórico de expectativa CE10, posteriormente corregido. Quedan 40 pruebas AF con proveedor real fuera de esa batería. No se encontró batería Node de ansiedad; no se declara ejecutada.',
       '', f"Auditoría offline actual: {citations} referencias literales comprobadas contra originales y solo historial anterior del mismo modelo; {len(errors)} errores; {len(replays)} repuntuaciones determinísticas de evidencia existente, {summary['replay_mismatches']} diferencias. JSON/CSV: 2.025 filas coincidentes. Esto no reemplaza el juicio semántico independiente.",
       '', 'PA8 original ChatGPT/1: 0, frente al 3 histórico conservado. Aplazar preocupaciones: 0; seguimiento real: 3. PS6 y GD7 originales ChatGPT/1: N/A por gates separados verificados mediante dos lecturas ciegas. Doce contrastes previos EM6/EM13/ND1 aceptados; no se repitieron.',
       '', f"Presupuesto nocturno adicional: US$7. Estado: {json.dumps(accounting(),ensure_ascii=False)}. Primer lote: dos intentos con fallo DNS getaddrinfo, incluso fuera del sandbox; cero respuestas de uso recibidas. No afirmar facturación cero definitiva: se retienen US$0,362034. No se ejecutaron reintentos ciegos. Gastos y reservas anteriores siguen intactos y no se transfieren fondos de CRISIS.",
       '', 'Histórico ansiedad previo: uso informado US$8,2270424; reservas inciertas US$1,0302248. La antigua disponibilidad conservadora era US$0,0694192 incluyendo la retención histórica CRISIS US$0,5733136. Esta autorización nocturna es independiente, no un límite histórico ni una compra de crédito. El saldo real de la cuenta no se pudo consultar.',
       '', f"Integridad CRISIS: {len(protected)} archivos comparados, {len(integrity['crisis_differences'])} diferencias. DOCX SHA256: {integrity['docx_sha256']}. Caché compartida no abierta. Sin cambios al frontend, runner general ni módulos protegidos en esta ejecución.",
       '', 'Pendientes exactos y causas: tables/observations.json y blocked_causes.json. BLOCKED y PENDING no son notas; excluyen porcentajes completos. N/A excluido del denominador. Los componentes contradictorios, citas inválidas y discrepancias no se convierten automáticamente en 0/3/N/A. No hay una nueva decisión humana impuesta por el fallo DNS; queda pendiente validar semánticamente el alcance restante.',
       '', 'Punto de recuperación: reparar la disponibilidad DNS/red del entorno antes de cualquier nueva llamada; conservar las dos reservas nocturnas hasta conciliación. Reanudar desde estas tablas, reutilizando todos los SCORED/N/A y los pares vigentes. No volver a diagnosticar, repetir 3.334 pruebas sin cambios ni repetir llamadas ya verificadas. night_validation.py conserva autorización estable y deduplicación del ledger; debe cargar estas tablas y las marcas de transporte antes de reanudar.',
       '', 'No existe validación clínica. No se declara cerrado ningún resultado incompleto.']
    (directory/'REPORT.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    save(directory/'files.json',[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha256(p.read_bytes()).hexdigest()} for p in directory.rglob('*') if p.is_file()])
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8');run(sys.argv[1])
