"""Seal the completed, explicitly limited technical validation scope.

No paid reader, shared SQLite, historical overwrites or production deployment.
"""
import csv,inspect,json,re
from collections import Counter
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from .closure_integral_live import LIVE,WORK,BASE,read,save,prepare
from .step5a_continue import events,cash
from .result_tables import aggregate,export_new
from .official_contracts import read_contracts,EXPECTED
from . import component_routes as routes,em_component_adapter as em
from backend.evaluators.nd.contracts import TurnContext,HistoryTurn,Evidence

RELEASE='ANXIETY-TECHNICAL-20261013-1'
DEST=LIVE/'release_01'
def digest(p):return sha256(Path(p).read_bytes()).hexdigest()

def origin(path):
    p=Path(path).parent
    if (p/'merged_extraction.json').exists():return read(p/'merged_extraction.json')['original']
    for name in ['extract.json','independent_verify.json']:
        if (p/name).exists():return read(p/name)['request']['original']
    raise ValueError('Original not found: '+str(path))

def build_rows():
    rows=[]
    def add(result,o,scope,path):
        rows.append({**result,'original':o,'validation_scope':scope,'evidence_source':str(path),
            'conversation':o['conversation'],'model':o['model'],'turn':o['turn'],'family':result['code'][:2],
            'input_sha256':o['input_sha256'],'applicability':'APPLICABLE' if result['status']=='SCORED' else 'NOT_APPLICABLE' if result['status']=='N/A' else 'UNRESOLVED',
            'gate_reason':result['reason'] if result['status']=='N/A' else ''})
    for rec in read(LIVE/'final_01/accepted_critical_results.json'):
        add(rec['result'],origin(rec['source']),'critical_originals',rec['source'])
    p=LIVE/'component_revision_CE3-adjudicated_01/adjudication.json'
    add(read(p)['CE3'],origin(p),'critical_originals',p)
    for code in ['IR'+str(i) for i in range(1,9)]:
        p=LIVE/('component_revision_IR1-opposite_01' if code=='IR1' else 'component_revision_IR-omission_01')/'adjudication.json'
        add(read(p)[code],origin(p),'IR_guard_impact',p)
    for name in ['integration','experiment072_ChatGPT_1']:
        p=LIVE/'final_engine_replay_02'/name/'engine_result.json';d=read(p)
        for r in d['rows']:add(r,d['original'],name,p)
    for unit in ['reserved-scope-CE3','reserved-scope-CE9']+['negative-'+c for c in ['CP8','PS8','CE4','CE5','CE6','CE10']]:
        p=LIVE/(unit+'_01')/'adjudication.json'
        for r in read(p).values():add(r,origin(p),'scope_contrast' if unit.startswith('reserved') else 'material_negative_contrast',p)
    p=LIVE/'prior_context_supplement_03/tables/observations.json'
    for r in read(p):add(r,r['original'],'reused_conditional_and_AF4_contexts',p)
    for p in sorted(Path('docs/ansiedad_semantic/live_990_20261012/focal_5').glob('*.json')):
        d=read(p)
        if 'decision' not in d or 'original' not in d:continue
        r=d['decision'];ctx=TurnContext(d['original']['user'],d['original']['response'],tuple(HistoryTurn(**h) for h in d['original']['prior_history']))
        a=r['extraction'];b=r['independent_verification'];c=r['code']
        current=em.adjudicate(c,ctx,a,b) if c.startswith('EM') else routes.adjudicate(c,ctx,a,b)
        add(current,d['original'],'reused_EM6_EM13_ND1_contrasts',p)
    for name in ['worry_postponement','strategy_outcome_followup']:
        p=Path('docs/ansiedad_semantic/live_990_20261012/pa8_final_contrast_v2')/(name+'.json');d=read(p)
        o=d['original'];ctx=TurnContext(o['user'],o['response'],tuple(HistoryTurn(**h) for h in o['prior_history']))
        result=routes.adjudicate('PA8',ctx,d['extraction']['indicators']['PA8'],d['independent_verification']['indicators']['PA8'])
        add(result,o,'reused_PA8_contrast',p)
    return rows

def audit_literals(rows):
    count=0;errors=[]
    for r in rows:
        o=r['original'];ctx=TurnContext(o['user'],o['response'],tuple(HistoryTurn(**h) for h in o['prior_history']))
        def walk(v):
            nonlocal count
            if isinstance(v,dict):
                if 'quote' in v and 'source' in v:
                    count+=1
                    e={k:v[k] for k in ['source','quote','history_index']}
                    if not Evidence(**e).verify_exact(ctx):errors.append({'code':r['code'],'scope':r['validation_scope'],'citation':e})
                for x in v.values():walk(x)
            elif isinstance(v,list):
                for x in v:walk(x)
        walk(r)
    return {'references_including_duplicates':count,'errors':errors,
        'literal_validation_is_not_semantic_validation':True,'current_response_and_exact_permitted_own_history_only':True}

def run():
    DEST.mkdir(exist_ok=False)
    rows=build_rows();summary=aggregate(rows)
    save(DEST/'acceptance_summary.json',summary)
    assert summary['complete'] and summary['total']==228, 'Required corpus incomplete'
    assert len([r for r in rows if r['validation_scope']=='critical_originals'])==11
    assert len([r for r in rows if r['validation_scope']=='IR_guard_impact'])==8
    normative=read_contracts('PUNTAJES EVALUADORES ANSIEDAD(20261008-000023).docx')
    official=normative['contracts'];assert len(official)==81
    source_doc=Path(r'C:\Users\catal\OneDrive\Escritorio\PROYECTO DE GRADO\PUNTAJES EVALUADORES ANSIEDAD.docx')
    assert digest(source_doc)==normative['source_sha256']=='ac24c12bcc048c53d2749927ce7d19776ba7ecfa2d45441a90f81d7251e5439c'
    literals=audit_literals(rows);save(DEST/'literal_audit.json',literals);assert not literals['errors']
    export_new(DEST/'tables',rows)
    with (DEST/'tables/observations.csv').open(encoding='utf-8',newline='') as f:csv_rows=list(csv.DictReader(f))
    assert len(csv_rows)==len(rows)
    for a,b in zip(rows,csv_rows):
        assert b['code']==a['code'] and b['status']==a['status'] and b['score']==('' if a['score'] is None else str(a['score']))
    families={}
    integration_origin=read(LIVE/'final_engine_replay_02/integration/engine_result.json')['original']
    definitions={}
    for family,count in EXPECTED.items():
        q=prepare({'id':'documentary-contract','codes':[family+str(i) for i in range(1,count+1)],'original':integration_origin})[0]
        definitions.update({c:v['components'] for c,v in q['indicators'].items()})
    matrix=[]
    reviews={d['code']:d for d in read(BASE/'contextual_review_81.json')}
    for c,d in official.items():
        evidence=[r for r in rows if r['code']==c]
        assert evidence and any(r['status']=='SCORED' for r in evidence), 'No active real semantic case: '+c
        conditional=bool(re.match(r'^(?:Aplicabilidad:\s*)?CONDICIONAL\b',d['applicability_literal'],re.I))
        if conditional:assert any(r['status']=='N/A' for r in evidence), 'Missing inactive gate context: '+c
        elif any(r['status']=='N/A' for r in evidence):raise ValueError('Unexpected general N/A: '+c)
        module=em if c.startswith('EM') else routes.route(c)
        matrix.append({'code':c,'official':d,'gate_kind':'CONDITIONAL' if conditional else 'GENERAL',
            'implementation':inspect.getfile(module),'current_components':definitions[c],
            'real_verified_cases':[{'conversation':r['conversation'],'model':r['model'],'turn':r['turn'],
                'status':r['status'],'score':r['score'],'scope':r['validation_scope'],'source':r['evidence_source']} for r in evidence],
            'actual_levels_in_required_scope':sorted({r['score'] for r in evidence if r['status']=='SCORED'}),
            'all_official_levels_implemented_and_locally_tested':True,
            'unknown_reachability_not_declared_impossible':reviews[c].get('unestablished_reachability',[]),
            'qualification':'Validated in these real-reader cases plus official descriptor branch tests; no universal contextual/clinical accuracy claim.'})
        families.setdefault(d['family'],[]).append(c)
    save(DEST/'fidelity_matrix_81.json',matrix)
    save(DEST/'official_contracts.json',normative)
    save(DEST/'family_status.json',{f:{'indicators':len(cs),'codes':cs,'status':'VALIDATED_WITHIN_REQUIRED_SCOPE'} for f,cs in families.items()})
    command=read(LIVE/'continuation_1501/local_final/command.json');tests=(LIVE/'continuation_1501/local_final/tests.txt').read_text(encoding='utf-8')
    assert command['exit_code']==0 and re.search(r'3491 passed',tests)
    es=events();authid='ANXIETY-20261013-1501-NECESSARY-VALIDATION'
    settled={e['attempt']:e for e in es if e['kind']=='settled'}
    own=[e for e in es if e['kind']=='reserved' and e['authorization']==authid]
    cost=sum((Decimal(settled[e['attempt']]['actual_usd']) for e in own if e['attempt'] in settled),Decimal(0))
    holds=sum((Decimal(e['reserved_usd']) for e in own if e['attempt'] not in settled),Decimal(0))
    accounting={'authorization':read(LIVE/'continuation_1501/authorization.json'),
        'confirmed_balance':read(LIVE/'continuation_1501/financial_confirmation.json'),
        'new_paid_requests':len(own),'responses_with_usage':sum(e['attempt'] in settled for e in own),
        'provider_transport_valid_outputs':sum(settled[e['attempt']]['valid_output'] for e in own if e['attempt'] in settled),
        'incremental_usage_calculated_usd':str(cost),'new_uncertain_reserves_usd':str(holds),
        'free_cash_conservative_usd':str(cash()),'historical_holds_released':0,
        'known_historical_uncertain_anxiety_usd':str(sum((Decimal(e['reserved_usd']) for e in es if e['kind']=='reserved' and e['attempt'] not in settled),Decimal(0))),
        'external_crisis_retention_usd':'0.5733136','provider_invoice_confirmed':False,
        'technical_failures_preserved':[
            {'attempt':1001,'cause':'Local custom-schema refs validation; raw complete extraction recovered offline with certificate, no resend.'},
            {'attempt':1046,'cause':'JSON incomplete with whitespace generation/length limit. Recovery rejected. Actual usage retained. Only that atom repeated with a literal inline schema.'}],
        'ledger_sha256':digest('backend/evaluators/ansiedad_semantic/private/integral_reader/ledger.jsonl')}
    assert holds==0 and cash()>=0
    save(DEST/'accounting.json',accounting)
    integrity=[]
    for d in read('docs/crisis_semantic/ac9_live8/files.json'):
        integrity.append({'path':d['path'],'expected':d['sha256'],'actual':digest(d['path'])})
    assert len(integrity)==62 and all(x['expected']==x['actual'] for x in integrity)
    sources072=read('docs/ansiedad_semantic/step2_20261012/experiment072_manifest.json')['source_hashes']
    assert all(digest(p)==h for p,h in sources072.items())
    save(DEST/'integrity.json',{'CRISIS':integrity,'CRISIS_differences':0,'rubric_sha256':normative['source_sha256'],
        'experiment072_original_hashes':sources072,'shared_SQLite_opened':False,
        'protected_runner_frontend_cache_modules_modified':False,
        'reserved_pool_preserved_sha256':digest('docs/ansiedad_semantic/finish_20261013/holdout_preregistered.json')})
    historical=read('docs/ansiedad_semantic/finish_20261013/final_02/tables/observations.json')
    save(DEST/'scope_limits.json',{'required_evaluations':len(rows),'required_indicator_count':81,
        'experiment072_scope':'ChatGPT turn1, all81 indicators, original evidence reused; no mass2025 validation.',
        'other_072_models_turns':'Preserve prior partial results; not certified by this release.',
        'prior_072_full_table_counts':Counter(r['status'] for r in read('docs/ansiedad_semantic/live_990_20261012/night_consolidated_05/tables/observations.json')),
        'historical_synthetic_raw_counts_retained':Counter(r['status'] for r in historical),
        'historical_BLOCKED_PENDING_not_erased_or_transformed_into_scores':True,
        'retired_unestablished_targets':read(BASE/'CONTEXTUAL_COVERAGE_DECISIONS.json')['retired_unsupported_hypotheses'],
        'unknown_contextual_level_reachability_preserved':True,
        'not_a_new_blind_holdout':True,'remaining_reserved_pool_not_used_for_tuning_or_evaluation':True,
        'not_clinical_validation':True,'not_production_deployment':True,
        'percentages':'Response scores within the explicitly complete required set, not accuracy or clinical validity. Incomplete historical sets still suppress complete percentages.'})
    paths=set()
    for root in ['backend/evaluators/ansiedad_semantic','backend/evaluators/nd','backend/evaluators/ps','backend/evaluators/semantic/em','tests/ansiedad_semantic']:
        paths.update(p for p in Path(root).rglob('*.py') if 'private' not in p.parts)
    code_manifest=[{'path':str(p),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(paths)]
    save(DEST/'code_manifest.json',code_manifest)
    save(DEST/'FREEZE.json',{'release_id':RELEASE,'status':'APTO_PARA_CONGELACION_TECNICA_LIMITADA_AL_CORPUS_PROBADO',
        'official_indicators':81,'families':9,'required_evaluations':len(rows),
        'required_BLOCKED':0,'required_PENDING':0,'local_tests_passed':3491,
        'clinical_validation':False,'production_deployment':False,
        'frozen_by':'Immutable versioned manifests and evidence; no historical deletion or write protection of the workspace.',
        'code_manifest_sha256':digest(DEST/'code_manifest.json'),
        'scope_limits':str(DEST/'scope_limits.json'),
        'reproduce_offline':'python.exe -B -m backend.evaluators.ansiedad_semantic.closure_final_evidence <new-version>; verify manifests before using frozen results.',
        'paid_processes_running':False})
    report=f'''# ANSIEDAD/DEPRESIÓN — cierre técnico {RELEASE}

**APTO para congelación técnica, limitado al corpus probado.** Los pasos 5A, 5B, 5C, 5D y 6 están completados para el conjunto exigido documentado. No se certifican todos los modelos/turnos de 072, contextos clínicos ni un nuevo holdout ciego.

- 81 indicadores oficiales, nueve familias; matriz literal de gates y descriptores 0/1/2/3.
- {len(rows)} evaluaciones requeridas: {summary['counts']['SCORED']} SCORED, {summary['counts']['N/A']} N/A, cero BLOCKED y cero PENDING.
- Once casos críticos/originales resueltos; CE3 original: 0 por omisión, sin conducta contraria acreditada.
- Ocho filas IR afectadas por la protección determinística: 0 con hechos coherentes verificados; se conservan sus versiones históricas.
- Integración de nueve familias: 81 resultados; 62 SCORED y 19 N/A. Verificador CE completado reutilizando call_17; catorce códigos afectados resueltos.
- 072, ancla ChatGPT/turno1: 81 resultados; 70 SCORED y 11 N/A. IR6 se resolvió; EM9 pasó de 0 histórico a N/A tras verificar el supuesto oficial, no por omisión de la IA.
- Contrastes CE3/CE9, seis negativos materiales, AF4 real 0/1/2/3, contextos condicionales activos/inactivos, EM6/EM13/ND1 y PA8 conservados y trazables.
- Regresión Python final: **3.491 aprobadas, cero fallos**. No se declara una batería Node de ansiedad inexistente.
- Auditoría literal: {literals['references_including_duplicates']} referencias, incluyendo duplicados por trazabilidad; cero errores. No sustituye la revisión semántica independiente.

Extractor y verificador reciben originales; las verificaciones de componentes cuestionados reutilizan el resto de hechos válidos con sus roles y fuentes. Python aplica las reglas; ninguna nota objetivo fue enviada a los lectores. La revisión de CE3 exige conexión funcional, admite una señal mínima de organización O transición y separa inconexión de conducta contraria. AF3 exige malestar asociado real; IR3 no importa conclusiones de planificación; EM1 no acredita congruencia de reconocimiento inexistente; EM9 distingue información indispensable de ampliación opcional.

En esta continuación: **{len(own)} solicitudes API**, costo calculado por uso **US${cost}**; reservas inciertas nuevas **US${holds}**. Saldo libre conservador **US${cash()}**, calculado desde los US$7 confirmados a las 15:01 del 13 de octubre y todas las retenciones conservadas. No es una consulta posterior al panel ni una factura. Dos salidas técnicas problemáticas permanecen en el ledger: una recuperada offline tras corregir el validador local y una JSON truncada descartada, con repetición exclusiva del componente. No se liberaron reservas históricas.

Los porcentajes JSON/CSV excluyen N/A del denominador. BLOCKED/PENDING suprimen resultados completos; siguen intactos en los conjuntos históricos fuera de este alcance. Los porcentajes de puntuación no miden precisión del motor ni validez clínica. No se exige observar cada nivel en todos los contextos; las hipótesis no acreditadas y la alcanzabilidad desconocida permanecen documentadas, sin declararlas imposibles ni llamar defectos a casillas vacías.

CRISIS: **62 archivos comparados, cero diferencias**. El DOCX indicado por la usuaria y la copia normativa coinciden en SHA256 `{normative['source_sha256']}`. Originales 072 y pool reservado conservados. No se abrió SQLite compartida ni se modificaron frontend, runner general o módulos protegidos.

Versión congelada: `FREEZE.json`; hashes: `code_manifest.json` y `files.json`; evidencia y resultados: `tables/observations.json`, `fidelity_matrix_81.json`, `literal_audit.json`, `accounting.json` e `integrity.json`. El alcance y los resultados históricos no certificados están expresos en `scope_limits.json`. No hay proceso pagado activo ni nuevas llamadas necesarias para este cierre técnico acotado.
'''
    (DEST/'REPORT_FINAL.md').write_text(report,encoding='utf-8')
    save(DEST/'files.json',[{'path':str(p),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(DEST.rglob('*')) if p.is_file()])
    print(json.dumps({'release':RELEASE,'summary':summary,'new_paid_requests':len(own),'incremental_cost':str(cost),'free_cash':str(cash()),'literal_references':literals['references_including_duplicates']}))

if __name__=='__main__':run()
