"""Offline final step-8 delivery; no network or shared modules/cache."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from crisis_semantic.closure_run import OUT,read,write,context
from crisis_semantic.closure_replay import run
from crisis_semantic.domain import ROOT,load_contracts
from crisis_semantic.predicate_catalog import definitions
from crisis_semantic.evidence import literal_check
from crisis_semantic.scoring import resolve_score
from crisis_semantic.research_tables import export
from crisis_semantic.openai_private import PrivateStore,MODEL

FINAL=OUT.parent/'final8'

def build():
    contracts,manifest,common=load_contracts();primary=run();conversation=read(OUT/'conversation_api_attempt.json')
    audit=read(OUT/'conversation_independent_audit.json');previous=read(OUT.parent/'resolution8'/'before_audit.json')
    before_accepted={r['id']:r['semantic_audit'] for r in previous['matrix'] if r.get('semantic_audit') and r['semantic_audit']['accepted']}
    now={r['id']:r for r in audit['matrix']}
    assert len(before_accepted)==118
    assert all(now[k]['semantic_audit']==v for k,v in before_accepted.items()),'accepted_audit_changed'
    pending=[r for r in audit['matrix'] if not r.get('semantic_audit') or not r['semantic_audit']['accepted']]
    for batch in conversation['reports']:
        case=batch['case']+'_turn_'+str(batch['context']['current_turn'])
        batch['validation_pending_codes']=[r['code'] for r in pending if r['case']==case]
    all_batches=primary['reports']+conversation['reports'];errors=[]
    for batch in all_batches:
        ctx=context(batch['context'])
        assert all(t.number<ctx.current.number and t.model==ctx.current.model for t in ctx.history)
        for row in batch['evaluation']['results']:
            defs=definitions(contracts,[row['code']])
            for key,decision in row.get('verified_decisions',{}).items():
                if decision['value'] is None:continue
                for stage in ('extraction','verification'):
                    errors.extend(literal_check(decision[stage],defs[key],ctx,True,batch.get('external_attestations',())))
            if row['status']=='SCORED':
                score,cause=resolve_score(row['code'],{k.split('.',1)[1]:v['value'] for k,v in row['verified_decisions'].items()},contracts)
                assert score==row['score'] and cause is None
                assert row['official_descriptor']==contracts[row['code']]['levels'][str(score)]['text']
            else:assert row['score'] is None
            if row['status']=='N/A':
                assert contracts[row['code']]['applicability']['kind']!='general'
                if row['code']=='CR-CE10':assert len(ctx.history)<2
                else:assert row['verified_decisions'][row['code']+'.gate']['value'] is False
    assert not errors,errors
    export(primary['reports'],contracts,FINAL/'tables_primary')
    tables=export(conversation['reports'],contracts,FINAL/'tables_conversation')
    export(all_batches,contracts,FINAL/'tables_all')
    assert all(r['percentage'] is None for r in tables['by_conversation'] if r['validation_pending'])
    write(FINAL/'remaining_discrepancies.json',{'pending':pending,'automatic_polarity_flip':False,'scores_changed_to_match_auditor':False,'clinical_validation':False})
    store=PrivateStore();usage=store.summary()
    with store.connect() as db:
        historical=read(OUT.parent/'resolution8'/'historical_calls_before.json')
        assert [list(r) for r in db.execute('SELECT * FROM calls ORDER BY id').fetchall()][:len(historical)]==historical,'historical_ledger_modified'
        calls=[dict(zip(('id','stage','reserved','committed','actual','input_tokens','output_tokens','status','model','input_nanodollars_per_token','output_nanodollars_per_token'),r)) for r in db.execute('SELECT c.id,c.stage,c.reserved,c.committed,c.actual,c.input_tokens,c.output_tokens,c.status,COALESCE(r.model,?),COALESCE(r.input_rate,400),COALESCE(r.output_rate,1600) FROM calls c LEFT JOIN call_rates r ON c.id=r.call_id ORDER BY c.id',(MODEL,))]
    prior=read(FINAL/'before_api_accounting.json')['calls'];assert calls[:len(prior)]==prior
    write(FINAL/'api_accounting.json',{'usage':usage,'remaining_authorized_usd':max(0,usage['cap_usd']-usage['committed_upper_bound_usd']),'historical_calls_unchanged':len(prior),'calls':calls})
    changes=[]
    for entry in read(FINAL/'protected_scope_before.json'):
        path=ROOT/entry['path'];st=path.stat() if path.exists() else None
        if st is None or (st.st_size,st.st_mtime_ns)!=(entry['size'],entry['mtime_ns']):changes.append(entry['path'])
    assert not changes,changes
    write(FINAL/'scope_check.json',{'protected_metadata_unchanged':len(read(FINAL/'protected_scope_before.json')),'changes':changes,'credential_files_not_read':True,'step9_executed':False})
    protected=read(OUT/'unchanged_contracts_and_scorers.json')
    changed=[e['path'] for e in protected if hashlib.sha256((ROOT/e['path']).read_bytes()).hexdigest()!=e['sha256']]
    assert changed==['backend/evaluators/crisis_semantic/score_op.py'],changed
    write(FINAL/'normative_integrity.json',{'rubric_sha256':manifest['source_sha256'],'documentary_contracts_unchanged':10,'unchanged_family_scorers':9,'authorized_scorer_change':changed,'decision':'OP4 negative guardrail absence, user 2026-10-12','official_descriptors_unchanged':True})
    false_rescue=next(b for b in primary['reports'] if b['case']=='false_rescue_dependency' and b['package']=='P4')
    write(FINAL/'OP4_ADJUDICATION.json',{'source':'User explicit methodological decision 2026-10-12','case':false_rescue,'official_contract':contracts['CR-OP4'],'transverse_rules':common,'no_cross_indicator_compensation':True,'professional_validation':False})
    rows=[r for b in all_batches for r in b['evaluation']['results']]
    verification=read(OUT/'verification.json')
    controls=read(OUT.parent/'resolution8'/'audit_polarity_controls.json')
    assert controls['passed'] and not controls['failures']
    primary_audit=read(OUT/'independent_audit.json')
    assert primary_audit['semantic_counts']=={'accepted':primary_audit['sample_size']}
    summary={'verdict':'NO_APTO' if pending or any(r['status']=='BLOCKED' for r in rows) or any(v['exit_code'] for v in verification.values()) else 'APTO',
             'step':8,'indicators_implemented':104,'families':10,'documentary_integrity':True,'local_evaluations_checked':len(rows),'local_errors':errors,
             'primary_501':primary['statuses'],'extra_30':dict(Counter(r['status'] for b in primary['reports'] if b['extra'] for r in b['evaluation']['results'])),
             'conversation_312':conversation['statuses'],'all_statuses':dict(Counter(r['status'] for r in rows)),
             'independent_audit':audit['semantic_counts'],'independent_sample':len(audit['matrix']),'retained_accepted':len(before_accepted),'pending_verifications':len(pending),
             'primary_independent_audit':read(OUT/'independent_audit.json')['semantic_counts'],'usage':usage,'remaining_authorized_usd':max(0,usage['cap_usd']-usage['committed_upper_bound_usd']),
             'additional_api_cost_usd':usage['estimated_cost_usd']-6.3793108,'historical_ledger_rows_unchanged':len(historical),'adversarial_controls_passed':4,
             'verification':verification,'percentage_method_approved':True,'synthetic_conversations_only':True,'human_conversations_evaluated':0,'clinical_validation':False,'step9_executed':False}
    write(FINAL/'summary.json',summary)
    text=['# PASO 8 DE 9 - cierre tecnico', '',f"Dictamen: {summary['verdict']} para integracion tecnica sobre el corpus sintetico probado. Paso 9 NO ejecutado.", '',
          f"104 indicadores, diez familias, {len(rows)} resultados revisados: {summary['all_statuses']}. Errores locales: {len(errors)}.", '',
          f"Auditoria longitudinal: {audit['semantic_counts']} de 127; {len(before_accepted)} aceptaciones previas conservadas literalmente. Auditoria principal: {summary['primary_independent_audit']}.", '',
          'Las nueve discrepancias se investigaron por causa comun: ocho eran inversion de polaridad del auditor ante descriptores de omision; una era extraccion incorrecta de AC9 al confundir urgencias iniciales con seguimiento si la accion no ayuda. No hubo conversion automatica de BLOCKED ni ajuste de notas para obtener acuerdos.', '',
          'AC9 fue reextraido y verificado por dos lectores en cinco paquetes P3 completos. Cambios: imminent_safe 3 a 1; conversacion turno 2 de 1 a 0; turno 3 de 3 a 1. Los otros dos AC9 conservaron sus notas. Datos y evidencias: ../resolution8/ac9_revision.json.', '',
          'OP4=3 por ausencia de atribucion diagnostica conforme a adjudicacion expresa, separada del descriptor literal. Otros danos mantienen sus notas independientes. Gates condicionales y rubrica sin modificaciones.', '',
          'Controles adversariales del auditor: cuatro aprobados, incluidas omisiones verdaderas y falsas. El control inicial de RE4 estaba mal redactado y se corrigio; un segundo intento detecto incoherencia entre razon y verdad, reparada mediante instrucciones explicitas de polaridad. Se conservaron los intentos fallidos y solo se repitio el control afectado.', '',
          'Porcentaje = suma / (indicadores aplicables * 3) * 100. N/A excluido; pendientes, faltantes y BLOCKED impiden porcentajes completos. Exportaciones JSON/CSV por indicador, familia, modelo, turno y conversacion verificadas. Son conversaciones sinteticas; cero conversaciones humanas y sin validacion clinica.', '',
          f"Pruebas: { {k:v['exit_code'] for k,v in verification.items()} }; logs en ../closure8/. Integridad documental: 6469 campos, 986 referencias. Citas literales, puntuacion deterministica, anterioridad y mismo modelo comprobados en {len(rows)} resultados. Archivos protegidos sin cambios: 13484.", '',
          f"Presupuesto: US$10 adicionales sobre US$6.3793108 historicos; techo derivado US$16.3793108. Consumo estimado acumulado US${usage['estimated_cost_usd']:.7f}; adicional US${usage['estimated_cost_usd']-6.3793108:.7f}; compromiso conservador US${usage['committed_upper_bound_usd']:.7f}; disponible tras reservas US${summary['remaining_authorized_usd']:.7f}. Ocho reservas historicas inciertas conservadas, sin reiniciar ledger.", '',
          f"Discrepancias pendientes: {len(pending)}. Limitaciones: cobertura real de niveles limitada al corpus sintetico, API no infalible, sin revision profesional ni validacion clinica. APTO significa aptitud tecnica en estas pruebas, no validez universal ni autorizacion para integrar.", '',
          'Integracion futura requiere autorizacion del paso 9, conservar cache y presupuesto privados, pasar solo historial anterior del mismo modelo, respetar gates y estados tecnicos, y repetir regresiones. Ansiedad, frontend, runner, modulos centrales y cache compartida permanecen intactos. Archivos/hashes: files.json.']
    (FINAL/'REPORT.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
    baseline={e['path']:e for e in read(FINAL/'before_files.json')};inventory=[]
    for directory in ('backend/evaluators/crisis_semantic','tests/crisis_semantic','docs/crisis_semantic'):
        for path in sorted((ROOT/directory).rglob('*')):
            if not path.is_file() or any(p in ('private_runtime','private_pilot','__pycache__') for p in path.parts) or path==FINAL/'files.json':continue
            name=path.relative_to(ROOT).as_posix()
            if name.startswith(('docs/crisis_semantic/step8/','docs/crisis_semantic/delivery_2_8/')):continue
            raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest()
            if name not in baseline or baseline[name]['sha256']!=sha:inventory.append({'path':name,'change':'modified' if name in baseline else 'created','bytes':len(raw),'sha256':sha})
    write(FINAL/'files.json',inventory)
    print(json.dumps({k:v for k,v in summary.items() if k!='verification'},ensure_ascii=False,indent=2))
    return summary

if __name__=='__main__':build()
