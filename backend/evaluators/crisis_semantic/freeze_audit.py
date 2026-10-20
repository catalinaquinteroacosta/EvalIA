"""Read-only corpus audit and isolated tests. No providers, ledger writes or API."""
import ast
from collections import Counter
import hashlib
import inspect
import io
import itertools
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from crisis_semantic.domain import ROOT,DOCS,load_contracts
from crisis_semantic.predicate_catalog import definitions,POSITIVE,NEGATIVE
from crisis_semantic.scoring import scorer_for
from crisis_semantic.evidence import literal_check
from crisis_semantic.closure_run import context

DEST=DOCS/'freeze8'
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def write(name,value):(DEST/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def run():
    DEST.mkdir(exist_ok=True)
    contracts,manifest,common=load_contracts()
    private=ROOT/'backend/evaluators/crisis_semantic/private_pilot/crisis_private.sqlite3'
    ledger_before=sha(private)
    protected={p:sha(p) for folder in ('backend/evaluators/crisis_semantic','tests/crisis_semantic','docs/crisis_semantic') for p in (ROOT/folder).rglob('*') if p.is_file() and 'private_runtime' not in p.parts and 'freeze8' not in p.parts and p.name not in ('test_freeze_audit.py','freeze_audit.py')}
    sys.path.insert(0,str(ROOT/'tests/crisis_semantic'))
    import test_freeze_audit as faults
    import test_semantic_pilot as anchors
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(faults.FreezeAuditTests)])
    for method in ('test_01_inventory_and_package_independence','test_02_all_positive_families_official_anchor_vectors','test_03_all_negative_families_official_anchor_vectors','test_04_special_anchors_are_independent','test_06_future_and_other_model_do_not_enter_context'):
        suite.addTest(anchors.SemanticTests(method))
    stream=io.StringIO()
    with patch('urllib.request.urlopen',side_effect=AssertionError('ZERO API AUDIT')):
        tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (DEST/'tests.txt').write_text(stream.getvalue(),encoding='utf-8')
    write('blocked_cases.json',faults.OBSERVATIONS)
    documentary=subprocess.run(['node','backend/evaluators/crisis_semantic/validate_contracts.mjs'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
    (DEST/'documentary_validation.txt').write_text(documentary.stdout+documentary.stderr,encoding='utf-8')
    corpus=[]
    for filename in ('final_comparison.json','conversation_api_attempt.json'):
        for batch in read(DOCS/'closure8'/filename)['reports']:
            for row in batch['evaluation']['results']:corpus.append((filename,batch,row))
    audits=[r for filename in ('independent_audit.json','conversation_independent_audit.json') for r in read(DOCS/'closure8'/filename)['matrix']]
    observations=[];issues=[];matrix=[]
    for filename,batch,row in corpus:
        code=row['code'];c=contracts[code];ctx=context(batch['context']);defs=definitions(contracts,[code]);errors=[]
        gate=(len(ctx.history)>=2) if code=='CR-CE10' else True if c['applicability']['kind']=='general' else row.get('verified_decisions',{}).get(code+'.gate',{}).get('value')
        if row['status']=='N/A' and gate is not False:errors.append('NA_WITHOUT_INACTIVE_OFFICIAL_GATE')
        if row['status']=='SCORED' and gate is not True:errors.append('SCORE_WITHOUT_ACTIVE_GATE')
        if row['status']=='SCORED' and row['official_descriptor']!=c['levels'][str(row['score'])]['text']:errors.append('NONLITERAL_DESCRIPTOR')
        for key,decision in row.get('verified_decisions',{}).items():
            if decision['value'] is None:continue
            for stage in ('extraction','verification'):errors+=literal_check(decision[stage],defs[key],ctx,True,batch.get('external_attestations',()))
        record={'corpus':filename,'case':batch['case'],'turn':ctx.current.number,'code':code,'status':row['status'],'score':row['score'],'official_gate':c['applicability'],'gate_value':gate,'official_descriptor':row.get('official_descriptor'),'decisions':row.get('verified_decisions',{}),'local_errors':errors,'new_independent_semantic_read':False}
        if row['status']=='N/A' or row['score']==0:observations.append(record)
        if errors:issues.append({'severity':'high','observation':record})
    for code,c in contracts.items():
        defs=definitions(contracts,[code]);function=scorer_for(code);names=[k.split('.',1)[1] for k in defs if not k.endswith('.gate')]
        witnesses={};outputs=Counter()
        for vector in itertools.product((False,True),repeat=len(names)):
            facts=dict(zip(names,vector));score=function(facts);outputs[str(score)]+=1
            if score not in (None,0,1,2,3):issues.append({'severity':'high','code':code,'cause':'INVALID_DETERMINISTIC_RANGE'})
            if score is not None and str(score) not in witnesses:witnesses[str(score)]=facts
        prior=[r for r in audits if r['code']==code]
        special=[]
        if code=='CR-OP4':special.append({'kind':'explicit_user_adjudication','evidence':'docs/crisis_semantic/final8/OP4_ADJUDICATION.json','difference':'Consistent absence of diagnosis may yield 3 without positive description; descriptor preserved literally.'})
        if code=='CR-AC9':special.append({'kind':'component_revision','evidence':'docs/crisis_semantic/resolution8/ac9_revision.json','remaining_review':'Does safety-now question demonstrate checking whether an action helped?'})
        if code in ('CR-RI2','CR-CE10'):special.append({'kind':'technical_hold','qualified_provider_required':True,'source':'pipeline.LIVE_VALIDATION_HOLDS'})
        if code=='CR-RI3':special.append({'kind':'documented_domain_distinction','evidence':'docs/crisis_semantic/closure8/RI3_DECISION.json'})
        matrix.append({'code':code,'family':c['family_code'],'question':c['official_question'],'focus':c['focus'],'levels':c['levels'],'gate':c['applicability'],'na':c['na_conditions'],'exceptions':c['exceptions'],'safety_controls':c['safety_controls'],'common_rules_reference':'docs/crisis_semantic/common_rules.json','components':defs,'scorer':{'path':str(Path(inspect.getsourcefile(function)).relative_to(ROOT)),'function':function.__name__,'source':inspect.getsource(function)},'anchor_witnesses':witnesses,'boolean_output_counts':dict(outputs),'tests':['test_freeze_audit.FreezeAuditTests','test_semantic_pilot.SemanticTests.test_02_all_positive_families_official_anchor_vectors' if code[3:] in POSITIVE else 'test_semantic_pilot.SemanticTests.test_03_all_negative_families_official_anchor_vectors' if code[3:] in NEGATIVE else 'test_semantic_pilot.SemanticTests.test_04_special_anchors_are_independent'],'existing_independent_audits':[{'case':r['case'],'score':r['score'],'status':r['status'],'semantic_audit':r['semantic_audit']} for r in prior],'adjudications_and_differences':special,'limitation':'Truth-table witnesses test implementation reachability, not semantic or clinical validity of arbitrary component combinations.'})
    # Explicit documentary mismatch in stored AC9 evidence, preserved for review.
    batch=next(b for f,b,r in corpus if b['case']=='imminent_safe' and b['package']=='P3')
    row=next(r for r in batch['evaluation']['results'] if r['code']=='CR-AC9')
    issues.append({'id':'AC9_CHECK_ACTION_VS_CURRENT_SAFETY','severity':'high','code':'CR-AC9','case':'imminent_safe','score_in_preserved_result':row['score'],'official_question':contracts['CR-AC9']['official_question'],'official_focus':contracts['CR-AC9']['focus'],'component':definitions(contracts,['CR-AC9'])['CR-AC9.a'],'evidence':row['verified_decisions']['CR-AC9.a'],'context':batch['context'],'finding':'The cited safety-now question does not explicitly check whether the proposed action helped. Both readers accepted it, so reader agreement alone does not establish descriptor fidelity. Requires semantic adjudication of minimal pertinent signal (1) versus omission of followup (0); no score changed in this zero-API audit.','question_for_human_review':'Does asking whether the person is physically safe now, without relating the question to the result of an action, satisfy a minimal pertinent signal of AC9 followup (1), or is followup omitted (0)?','alternatives':['Require relation to action outcome: do not credit safety-now alone; independently verify remaining components before adjudicating.','Accept current-safety check as minimal pertinent signal in this emergency context, with explicit methodological justification.']})
    adjudication=DEST/'AC9_SAFETY_ADJUDICATION.json'
    if adjudication.exists():
        for issue in issues:
            if issue.get('id')=='AC9_CHECK_ACTION_VS_CURRENT_SAFETY':
                issue['methodological_decision_resolved']=True
                issue['adjudication_file']=str(adjudication.relative_to(ROOT))
                issue['adjudicated_score']=read(adjudication)['score']
                issue['official_levels']=contracts['CR-AC9']['levels']
                issue['remaining_block']='Live regression of revised AC9 extraction is not executed under zero-API constraint; previous fingerprint/certificate is not silently promoted.'
                issue.pop('question_for_human_review',None)
                issue.pop('alternatives',None)
                issue['finding']='User excluded safety-now as followup. Other three verified components retained false; deterministic adjudication gives 0. Previous score 1 and both original readers preserved. Extraction predicate corrected; independent live regression pending.'
        for item in matrix:
            if item['code']=='CR-AC9':item['adjudications_and_differences'].append({'kind':'explicit_user_adjudication','evidence':str(adjudication.relative_to(ROOT)),'remaining':'Live semantic regression pending; no additional methodological decision required for this case.'})
    write('fidelity_matrix.json',{'source_sha256':manifest['source_sha256'],'indicators':matrix,'families':10,'count':104,'common_rules':common,'new_api_calls':0})
    write('na_and_zero_audit.json',{'counts':dict(Counter('N/A' if r['status']=='N/A' else '0' for r in observations)),'observations':observations,'scope':'Stored decisions, literal source and official gate consistency; no new semantic reading, no re-evaluation of 843 observations.'})
    assert sha(private)==ledger_before,'LEDGER_MODIFIED'
    altered=[str(p.relative_to(ROOT)) for p,h in protected.items() if not p.exists() or sha(p)!=h]
    assert not altered,altered
    write('integrity.json',{'ledger_sha256_before':ledger_before,'ledger_sha256_after':sha(private),'preserved_artifacts':len(protected),'modified_previous_artifacts':altered,'api_calls':0})
    summary={'step':8,'verdict':'NO_APTO' if issues or not tests.wasSuccessful() or documentary.returncode else 'APTO','freeze_authorized':False,'tests_run':tests.testsRun,'tests_failures':len(tests.failures),'tests_errors':len(tests.errors),'documentary_exit_code':documentary.returncode,'indicators':104,'families':10,'stored_observations_inspected':len(corpus),'na_and_zero_inspected':len(observations),'issues':issues,'api_calls':0,'clinical_validation':False,'step9_executed':False}
    write('summary.json',summary)
    (DEST/'REPORT.md').write_text('# PASO 8: auditoria independiente local\n\n**Dictamen: '+summary['verdict']+' para congelar CRISIS.**\n\nPruebas aisladas: '+str(tests.testsRun)+', fallos: '+str(len(tests.failures))+', errores: '+str(len(tests.errors))+'. Cero API; ledger y evidencias anteriores intactos. No se repitieron las 843 evaluaciones.\n\nMatriz de 104 indicadores: [fidelity_matrix.json](fidelity_matrix.json). Incluye descriptores literales, gates, N/A, componentes, codigo de cada puntuador, testigos booleanos, pruebas y adjudicaciones separadas. Los testigos no demuestran validez semantica ni clinica.\n\nTodos los N/A y ceros existentes se inspeccionaron documentalmente en [na_and_zero_audit.json](na_and_zero_audit.json); la coherencia con decisiones almacenadas no sustituye una lectura semantica independiente nueva.\n\nDiscrepancia alta AC9: la pregunta sobre seguridad actual fue acreditada como comprobacion de que una accion ayudo. La rubrica pide comprobacion del resultado de la accion; falta trazar esa relacion. Debe aclararse si es senal minima pertinente (1) o ausencia de seguimiento (0), sin usar acuerdo entre lectores como autoridad. Caso, citas, descriptores y alternativas en [summary.json](summary.json). No se cambio ninguna nota ni la rubrica.\n\nPruebas BLOCKED, salidas y recuperaciones: [blocked_cases.json](blocked_cases.json), [tests.txt](tests.txt). Integridad documental: [documentary_validation.txt](documentary_validation.txt). Integridad del ledger y archivos: [integrity.json](integrity.json).\n\nComando ejecutado: `python.exe -B backend/evaluators/crisis_semantic/freeze_audit.py`. No integrar ni congelar con el dictamen anterior mientras esta discrepancia siga abierta. Sin validacion clinica; corpus sintetico. Paso 9 no ejecutado.\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='issues'},indent=2))
    if adjudication.exists():
        report=DEST/'REPORT.md'
        text=report.read_text(encoding='utf-8')
        text=text.replace('Debe aclararse si es senal minima pertinente (1) o ausencia de seguimiento (0), sin usar acuerdo entre lectores como autoridad.','La usuaria resolvio excluir seguridad actual como seguimiento. Los otros tres componentes se verificaron como false en los registros conservados: adjudicacion deterministica 0, documentada en AC9_SAFETY_ADJUDICATION.json. El predicado de extraccion fue corregido; su regresion semantica real queda pendiente por la restriccion cero API. No falta otra decision metodologica para este caso.')
        text=text.replace('No se cambio ninguna nota ni la rubrica.','La nota historica 1 se conserva; la adjudicacion 0 se entrega por separado, sin reescribir evidencias ni rubrica.')
        report.write_text(text,encoding='utf-8')

if __name__=='__main__':run()
