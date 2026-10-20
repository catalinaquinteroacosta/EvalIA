"""Append-only documentary checkpoint; no provider, cache or scoring mutations."""
import json
from collections import Counter
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from .closure_integral_live import LIVE, WORK, BASE, source, prepare, estimate, MODEL
from .step5a_continue import cash, events

def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def digest(p): return sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):
    with Path(p).open('x',encoding='utf-8') as f: json.dump(d,f,ensure_ascii=False,indent=2)

def run():
    out=LIVE/'final_01';out.mkdir(exist_ok=False)
    accepted_sources={
        'PA1':WORK/'continue_5A_PA1/adjudication.json',
        'PS6':WORK/'continue_5A_PS6/adjudication.json',
        'IR2':LIVE/'IR2_01/adjudication.json',
        'CE9':LIVE/'CEscope_01/adjudication.json',
        'CP6':LIVE/'critical-CP6_02/adjudication.json',
        'PA3':LIVE/'PA3-adjudicated_01/adjudication.json',
        'GD2':LIVE/'critical-GD2_01/adjudication.json',
        'GD8':LIVE/'critical-GD2_01/adjudication.json',
        'GD7':LIVE/'GD7-only_01/adjudication.json',
        'PA6':LIVE/'critical-PA6_01/adjudication.json'}
    accepted=[]
    for code,p in accepted_sources.items():
        r=read(p)[code]
        assert r['status']=='SCORED'
        accepted.append({'code':code,'result':r,'source':str(p),'sha256':digest(p),
            'acceptance':'Literal evidence and contextual meaning reviewed; canonical Python result, not historical agreement.'})
    save(out/'accepted_critical_results.json',accepted)
    ce3=read(LIVE/'CE3-functional_02/adjudication.json')['CE3']
    save(out/'CE3_UNCERTIFIED.json',{'current_status':'BLOCKED_SEMANTIC_CERTIFICATION','certified_score':None,
        'raw_python_score':ce3['score'],'raw_source':str(LIVE/'CE3-functional_02/adjudication.json'),
        'reason':'Readers infer that the refusal explains the weather sentence through the user topic. The referent of lo que acabas de contar is the user contribution, not an established functional connection between the two AI ideas. Raw concordance does not resolve this unsupported relational inference.',
        'human_decision':'Exigir conexión funcional comprensible entre ideas',
        'next_action':'Require a grounded relation with both response-idea endpoints; retain raw readings and diagnose relational proof before any further paid attempt.'})
    save(out/'METHODOLOGICAL_DECISIONS.json',{
        'PA3':{'authority':'Latest explicit user reply: Admitir como señal mínima de qué hacer',
            'implementation':'Tool-use instruction counts as recognizable minimal what, not sufficient how/full execution.',
            'reused_verification':str(LIVE/'critical-PA3_02/independent_verify.json'),
            'new_extraction':str(LIVE/'PA3-adjudicated_01/extract.json'),
            'rubric_unchanged':True},
        'CE3':{'authority':'User: Exigir conexión funcional comprensible entre ideas',
            'live_certification':'Not resolved for weather/refusal original; integration CE3 is a separate fully structured response.'},
        'GD7':{'change':'Explicit essential/full conjunction and preserved part; required limits omission is separate from absence of role claim.',
            'numeric_algorithm_changed':False},
        'functional_guard':{'change':'Contradictory secondary defect with absent central function now BLOCKED.',
            'impact':str(LIVE/'impact_guard_revision.json'),'historical_scores_overwritten':False}})
    engine=read('docs/ansiedad_semantic/finish_20261013/step3_engine_01/engine_result.json')
    replacements={}
    for name in ['CEverify_CE1_CE2_01','CEverify_CE3_01']:
        p=LIVE/name/'adjudication.json'
        for c,r in read(p).items():replacements[c]={'result':r,'source':str(p)}
    save(out/'integration_new_verified_results.json',replacements)
    save(out/'integration_status.json',{'baseline': 'docs/ansiedad_semantic/finish_20261013/step3_engine_01/engine_result.json',
        'baseline_rows':len(engine['rows']),'new_independently_verified_CE_codes':list(replacements),
        'pending_CE_codes':['CE4','CE5','CE6','CE7','CE8','CE9','CE10'],
        'affected_other_codes':['AF1','AF2','AF3','AF4','ND3','ND4','ND5','ND6','ND8','CP1','IR1','IR3','EM1','EM2'],
        'complete':False,'complete_percentage':None,'saved_17_calls_repeated':False})
    units=['CE3-functional','reserved-scope-CE3','reserved-scope-CE9',
        'integration-affected-AF','integration-affected-ND','integration-affected-CP','integration-affected-IR','integration-affected-EM']
    units += ['CEverify:'+c for c in ['CE4','CE5','CE6','CE7','CE8','CE9','CE10']]
    units += ['IR-omission:'+','.join('IR'+str(i) for i in range(1,9))]
    units += ['negative-'+c for c in ['CP8','CE4','CE5','CE6','CE10','PS8']]
    pending=[]
    for unit in units:
        case,reuse=source(unit);qs=prepare(case)
        if reuse is not None:qs=[q for q in qs if q['stage']=='independent_verify']
        plans=[]
        for q in qs:
            q['_max_output_tokens']=min(28000,max(4000,sum(len(v['components']) for v in q['indicators'].values())*240))
            q['instruction']+=' Distingue omisión de conducta contraria y defecto principal de secundario. Para CE3/CE9 examina estructura real, sin pertinencia temática. No selecciones notas.'
            plans.append({'stage':q['stage'],'estimate':estimate(q,MODEL)})
        bound=sum((Decimal(x['estimate']['reserved_upper_bound_usd']) for x in plans),Decimal(0))
        pending.append({'unit':unit,'codes':case['codes'],'original_sha256':case['original']['input_sha256'],
            'requests':plans,'configured_upper_usd':str(bound),'financially_covered_now':bound<=cash(),
            'not_sent':True,'scope':'Critical original' if unit=='CE3-functional' else 'Existing targeted material validation; not mass coverage',
            'execution_condition':'Fresh contract/hash/dedup/cash check. CE3 relational failure needs diagnosis first; no identical blind retry.'})
    save(out/'remaining_source_and_financial_checks.json',pending)
    assert not any(p['financially_covered_now'] for p in pending)
    es=events();settled={e['attempt']:e for e in es if e['kind']=='settled'}
    own=[e for e in es if e['kind']=='reserved' and e['authorization']=='ANXIETY-20261013-INTEGRAL-REMAINING-CASH']
    accounting={'global_authorization_attempts':len(own),'completed_with_usage':sum(e['attempt'] in settled for e in own),
        'incremental_usage_calculated_usd':str(sum((Decimal(settled[e['attempt']]['actual_usd']) for e in own if e['attempt'] in settled),Decimal(0))),
        'new_uncertain_reserves_usd':str(sum((Decimal(e['reserved_usd']) for e in own if e['attempt'] not in settled),Decimal(0))),
        'free_cash_conservative_usd':str(cash()),'balance_basis':'Prior user-confirmed USD4 less subsequent calculated use and all unresolved holds; no fresh billing-panel balance.',
        'all_anxiety_uncertain_holds_usd':str(sum((Decimal(e['reserved_usd']) for e in es if e['kind']=='reserved' and e['attempt'] not in settled),Decimal(0))),
        'external_crisis_hold_usd':'0.5733136','holds_released':0,'provider_invoice_confirmed':False}
    save(out/'accounting.json',accounting)
    matrix=[]
    for row in read(BASE/'contextual_review_81.json'):
        c=row['code'];matrix.append({'code':c,'official':row['official'],'offline_contextual_review_source':str(BASE/'contextual_review_81.json'),
            'offline_review_complete':True,'implementation_not_equivalent_to_validation':True,
            'accepted_critical_cases':[{'source':a['source'],'score':a['result']['score']} for a in accepted if a['code']==c],
            'new_integration_verified':replacements.get(c),
            'remaining_units':[p['unit'] for p in pending if c in p['codes']],
            'semantic_validation_scope':'Partial; existing contextual review retained. No whole-indicator/global certification.'})
    assert len(matrix)==81
    save(out/'fidelity_matrix_81.json',matrix)
    crisis=[]
    for item in read('docs/crisis_semantic/ac9_live8/files.json'):
        p=Path(item['path']);crisis.append({'path':str(p),'expected':item['sha256'],'actual':digest(p),'matches':digest(p)==item['sha256']})
    rubric=Path('PUNTAJES EVALUADORES ANSIEDAD(20261008-000023).docx')
    originals=[{'path':p,'expected':h,'actual':digest(p),'matches':digest(p)==h} for p,h in read('docs/ansiedad_semantic/step2_20261012/experiment072_manifest.json')['source_hashes'].items()]
    integrity={'CRISIS':crisis,'CRISIS_differences':sum(not c['matches'] for c in crisis),
        'rubric_sha256':digest(rubric),'rubric_matches':digest(rubric)=='ac24c12bcc048c53d2749927ce7d19776ba7ecfa2d45441a90f81d7251e5439c',
        'experiment072_sources':originals,'shared_SQLite_opened':False,'protected_modules_modified':False}
    assert integrity['CRISIS_differences']==0 and integrity['rubric_matches'] and all(x['matches'] for x in originals)
    save(out/'integrity.json',integrity)
    save(out/'RECOVERY.json',{'verdict':'NO APTO','paid_processes_running':False,'cash_block_demonstrated':True,
        'remaining':str(out/'remaining_source_and_financial_checks.json'),'accepted':str(out/'accepted_critical_results.json'),
        'critical_originals_resolved':10,'critical_originals_total':11,'uncertified_original':'CE3',
        'guard_impact_eight_IR_rows':str(LIVE/'impact_guard_revision.json'),
        'next_action':'Reconcile actual balance and unresolved billing holds without releasing unsupported reservations. After covered funding exists, diagnose CE3 relational grounding and execute only pending original/contract-specific requests. Reuse accepted critical results and CE1/2/3 integration; do not repeat diagnostics, valid calls, full suite without relevant change or mass072.',
        'local_regression':str(LIVE/'local_final_01/command.json'),'local_passed':3468,
        'steps':{'5A':'CE3 certification BLOCKED','5B':'Six original cases verified','5C':'Partial integration and scope contrasts pending','5D':'Partial semantic fidelity, eight new guard-impact rows unresolved','6':'Not eligible for freeze'},
        'N/A_excluded_from_denominator':True,'BLOCKED_PENDING_prevent_complete_percentage':True,
        'complete_percentage':None,'clinical_validation':False})
    family_counts=Counter(r['official']['family'] for r in matrix)
    text='# ANSIEDAD — continuación integral, recuperación final\n\n**NO APTO para congelación.** Diez de los once casos críticos/originales están verificados; CE3 conserva una inferencia relacional no acreditada. No se declara cierre por concordancia numérica.\n\n'
    text+='| Código | Resultado verificado |\n|---|---:|\n'+''.join('| '+a['code']+' | '+str(a['result']['score'])+' |\n' for a in accepted)
    text+='\nPA3 incorpora la decisión expresa de admitir la instrucción de herramienta como señal mínima de qué hacer. Se reutilizó su verificación válida y se obtuvo una extracción nueva. GD7 distingue ausencia de rol falso de aclaración de límites requerida; gate y omisión total verificados. CE3 de integración es otro original con secuencia explícita y quedó verificado en 3; no resuelve CE3 del original meteorológico.\n\n'
    text+='Regresión local posterior a los cambios: **3.468 aprobadas, cero fallos** (`../local_final_01`). La guardia determinística contra defecto secundario con función central ausente revela ocho filas IR-omission antes puntuadas: ahora BLOCKED en reproducción, sin sobrescribir historia. Los componentes simulados no certifican lectores reales.\n\n'
    text+=f"Esta autorización integral registra **{accounting['completed_with_usage']} respuestas API con uso**, {accounting['global_authorization_attempts']} intentos, costo incremental calculado **US${accounting['incremental_usage_calculated_usd']}**, reservas nuevas inciertas **US${accounting['new_uncertain_reserves_usd']}**. No son factura. Saldo libre conservador **US${cash()}**; ningún paquete pendiente preparado cabe con su reserva íntegra. CE8 fue detenido antes de enviar; cero reservas liberadas.\n\n"
    text+='Las nueve familias conservan revisión offline de '+str(dict(family_counts))+'; implementación y pruebas locales no equivalen a validación integral. Integración CE1/CE2/CE3 verificada; faltan siete CE y los catorce códigos afectados de otras familias. Faltan los dos contrastes de alcance y las validaciones materiales indicadas en remaining_source_and_financial_checks.json. No se recorren las 101 contingencias ni 072 completo.\n\n'
    text+='CRISIS: 62 archivos, cero diferencias. DOCX y originales 072 conservan hashes. No se abrió SQLite compartida ni se modificaron frontend, runner general o módulos protegidos. N/A excluido del denominador; BLOCKED/PENDING y alertas impiden porcentaje completo.\n\nRecuperación exacta en RECOVERY.json; evidencias literales en accepted_critical_results.json e integration_new_verified_results.json; matriz oficial de 81 códigos en fidelity_matrix_81.json. No hay proceso pagado activo ni validación clínica. El impedimento financiero es cobertura insuficiente conservando reservas, además de la validación semántica restante; la autorización de alcance de la usuaria sigue registrada y no se pide permiso de nuevo por cada corrección.\n'
    (out/'REPORT.md').write_text(text,encoding='utf-8')
    save(out/'files.json',[{'path':str(p),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(out.iterdir()) if p.is_file()])
    print(json.dumps(accounting));print('checkpoint',out)

if __name__=='__main__':run()
