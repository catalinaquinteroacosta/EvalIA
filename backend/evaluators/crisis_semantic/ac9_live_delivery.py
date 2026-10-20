"""Versioned offline delivery after focal semantic regression; no API calls."""
import copy
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from crisis_semantic.domain import ROOT,DOCS,load_contracts,digest
from crisis_semantic.closure_run import OUT,read,write
from crisis_semantic.span_provider import fingerprint,CERTIFICATE,PROMPT,VERIFY
from crisis_semantic.predicate_catalog import definitions
from crisis_semantic.research_tables import export
from crisis_semantic.openai_private import PrivateStore

DEST=DOCS/'ac9_live8'
def run():
    latest=max(DEST.glob('regression_attempt_*.json'),key=lambda p:int(p.stem.rsplit('_',1)[1]))
    regression=read(latest);assert regression['passed'] and not regression['findings']
    contracts,manifest,_=load_contracts();current=definitions(contracts,list(contracts))
    oldns=runpy.run_path(str(DOCS/'freeze8/predicate_catalog_before_safety_adjudication.py.txt'))
    olddefs=oldns['definitions'](contracts,list(contracts))
    differences=[k for k,v in current.items() if v!=olddefs[k]]
    assert set(differences)=={'CR-AC9.a','CR-AC9.b'},differences
    before_provider=runpy.run_path(str(DEST/'span_provider_before_certificate_loader.py.txt'),run_name='crisis_semantic._historical_provider')
    assert (PROMPT,VERIFY)==(before_provider['PROMPT'],before_provider['VERIFY'])
    proof=copy.deepcopy(read(CERTIFICATE));original=copy.deepcopy(proof)
    baseline=read(OUT/'final_comparison.json');conversation=read(OUT/'conversation_api_attempt.json')
    for code,checks in proof['components'].items():
        assert all(current[k]==olddefs[k] for k in definitions(contracts,[code]))
        for check in checks:
            row=next(r for b in baseline['reports'] if b['case']==check['case'] for r in b['evaluation']['results'] if r['code']==code)
            assert (row['score'] if row['status']=='SCORED' else row['status'])==check['expected']
    write(DEST/'historical_qualification.json',original)
    proof.update(fingerprint=fingerprint(),ac9_live_revision={'changed_predicates':differences,'unchanged_RI2_CE10_components':True,'previous_fingerprint':original['fingerprint'],'API_prompts_unchanged':True,'regression_file':latest.name,'loader_change_only_adds_versioned_qualification':True})
    write(DEST/'qualification.json',proof)
    changes=[]
    for item in regression['cases']:
        if item['case'].startswith('primary_'):data=baseline;corpus='primary'
        elif item['case'].startswith('conversation_'):data=conversation;corpus='conversation'
        else:continue
        for batch in data['reports']:
            identity=corpus+'_'+batch['case']+'_'+str(batch['context']['current_turn'])
            if identity!=item['case'] or batch['package']!='P3':continue
            for n,row in enumerate(batch['evaluation']['results']):
                if row['code']=='CR-AC9':
                    changes.append({'case':identity,'historical_score':row['score'],'current_score':item['after']['score'],'historical_descriptor':row['official_descriptor'],'current_descriptor':item['after']['official_descriptor']})
                    batch['evaluation']['results'][n]=copy.deepcopy(item['after'])
            batch['evaluation']['issues']=[i for i in batch['evaluation']['issues'] if not i.get('id','').startswith('CR-AC9.')]
    for data in (baseline,conversation):data['fingerprint']=fingerprint()
    baseline['qualification']=proof
    baseline['statuses']=dict(Counter(r['status'] for b in baseline['reports'] if not b['extra'] for r in b['evaluation']['results']))
    conversation['statuses']=dict(Counter(r['status'] for b in conversation['reports'] for r in b['evaluation']['results']))
    write(DEST/'final_comparison.json',baseline);write(DEST/'conversation_api_attempt.json',conversation)
    write(DEST/'release.json',{'semantic_regression_passed':True,'regression_file':latest.name,'fingerprint':fingerprint(),'freeze_verdict':'PENDING_LOCAL_TESTS','step':8,'step9_executed':False})
    write(DEST/'comparison.json',{'changes':changes,'changed_components':differences,'historical_evidence_overwritten':False,'qualification_transfer':proof['ac9_live_revision']})
    tables=export(baseline['reports']+conversation['reports'],contracts,DEST/'tables')
    assert not any(r['status']=='BLOCKED' for r in tables['observations'])
    commands={'python_tests':[sys.executable,'-B','-m','unittest','discover','-s','tests/crisis_semantic','-p','test_*.py','-v'],'node_tests':['node','--test','--test-reporter=tap','tests/crisis_semantic/contracts.test.mjs'],'documentary_validation':['node','backend/evaluators/crisis_semantic/validate_contracts.mjs']}
    def execute(item):
        name,command=item;result=subprocess.run(command,cwd=ROOT,capture_output=True,encoding='utf-8',errors='replace')
        log=DEST/(name+'.txt');log.write_text(result.stdout+result.stderr,encoding='utf-8')
        return name,{'command':command,'exit_code':result.returncode,'log':str(log.relative_to(ROOT)),'sha256':hashlib.sha256(log.read_bytes()).hexdigest()}
    with ThreadPoolExecutor(max_workers=3) as pool:tests=dict(pool.map(execute,commands.items()))
    write(DEST/'verification.json',tests)
    usage=PrivateStore().summary();before=read(DEST/'usage_before.json')
    with PrivateStore().connect() as db:
        prior=read(DEST/'historical_calls_before.json');allcalls=[list(r) for r in db.execute('SELECT * FROM calls ORDER BY id').fetchall()];assert allcalls[:len(prior)]==prior
    write(DEST/'api_accounting.json',{'usage':usage,'incremental_calls':usage['calls']-before['calls'],'incremental_cost_usd':usage['estimated_cost_usd']-before['estimated_cost_usd'],'calls_added':allcalls[len(prior):],'historical_calls_unchanged':len(prior),'uncertain_reservations_preserved':usage['statuses'].get('unknown_billing')==before['statuses'].get('unknown_billing')})
    protected=read(DOCS/'final8/protected_scope_before.json');scope=[]
    for entry in protected:
        p=ROOT/entry['path'];st=p.stat() if p.exists() else None
        if st is None or (st.st_size,st.st_mtime_ns)!=(entry['size'],entry['mtime_ns']):scope.append(entry['path'])
    assert not scope,scope
    write(DEST/'scope.json',{'protected_files_unchanged':len(protected),'changes':scope,'step9_executed':False})
    summary={'step':8,'verdict':'APTO' if not any(t['exit_code'] for t in tests.values()) else 'NO_APTO','scope':'Freeze technically on tested synthetic corpus; no clinical validation.','semantic_cases':8,'independent_descriptor_assertions':8,'findings_remaining':[],'statuses':dict(Counter(r['status'] for r in tables['observations'])),'historical_results_preserved':843,'indicators':104,'families':10,'incremental_calls':usage['calls']-before['calls'],'incremental_cost_usd':usage['estimated_cost_usd']-before['estimated_cost_usd'],'usage':usage,'remaining_authorized_usd':usage['cap_usd']-usage['committed_upper_bound_usd'],'tests':tests,'clinical_validation':False,'step9_executed':False}
    write(DEST/'summary.json',summary)
    release=read(DEST/'release.json');release['freeze_verdict']=summary['verdict'];write(DEST/'release.json',release)
    lines=['# PASO 8 - regresion focalizada AC9 y cierre versionado','',f"**Dictamen: {summary['verdict']} para congelar CRISIS, limitado al corpus sintetico probado.** Sin validacion clinica. Paso 9 no ejecutado.",'','## Resultados semanticos','',
           'Ocho casos: cinco existentes y tres pares de contraste. Extraccion y verificacion ciegas con citas literales; auditor independiente de correspondencia de descriptores. Solo Python asigna notas. Resultados completos en '+latest.name+'.','',
           '| Caso | Antes | Ahora |','|---|---:|---:|']
    for change in changes:lines.append(f"| {change['case']} | {change['historical_score']} | {change['current_score']} |")
    lines+=['','Controles: seguridad actual sin seguimiento = 0; seguimiento minimo = 1; seguimiento completo = 3. La comprobacion inicial no prueba el resultado de una accion. El primer intento produjo una regresion en AC9.b (urgencias iniciales confundidas con falta de ayuda); fue rechazado, corregido y repetido solo b. No se acepta simple concordancia numerica. first_attempt_rejection.json conserva el error; siete auditorias no afectadas se reutilizaron.','',
            'Los demas componentes a/c/opposite se reutilizaron en la correccion de b. Los 29 indicadores restantes de cada paquete P3 conservaron sus resultados; no se reejecutaron las 843 evaluaciones mediante API. Nueva version en final_comparison.json y conversation_api_attempt.json; originales intactos. Adjudicacion historica 1 -> 0 trazable en comparison.json y ../freeze8/AC9_SAFETY_ADJUDICATION.json.','',
            f"Estados del corpus actualizado: {summary['statuses']}. BLOCKED nunca se transforma automaticamente; N/A depende del gate. Pruebas de fallos, porcentajes, gate y longitudinalidad en python_tests.txt. Formula aprobada: suma/(aplicables*3)*100, excluyendo N/A; pendientes o BLOCKED impiden porcentaje completo. JSON/CSV exportados en tables/.",'',
            f"API incremental: {summary['incremental_calls']} llamadas; US${summary['incremental_cost_usd']:.7f}. Acumulado US${usage['estimated_cost_usd']:.7f}; compromiso conservador US${usage['committed_upper_bound_usd']:.7f}; presupuesto autorizado disponible tras reservas US${summary['remaining_authorized_usd']:.7f}. Ocho reservas inciertas intactas. Esto no es una consulta del saldo de cuenta OpenAI. Ledger completo sin reinicio; 442 llamadas historicas intactas.",'',
            f"Pruebas: { {k:v['exit_code'] for k,v in tests.items()} }. Integridad documental contra DOCX vigente; 104 indicadores, 416 descriptores. Contexto anterior del mismo modelo, evidencias y salvaguardas preservadas. Certificado RI2/CE10 versionado: se comprueba invariancia de sus componentes y controles historicos; no se repiten llamadas ajenas a AC9.",'',
            'Sin discrepancias pendientes en esta regresion. Limitaciones: corpus sintetico, no conversaciones humanas, lectores API falibles y sin revision profesional. La correccion no demuestra validez universal. Ansiedad, frontend, runner, modulos centrales y cache compartida intactos. No hay autorizacion ni ejecucion del paso 9.']
    (DEST/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('tests','usage')},indent=2))

if __name__=='__main__':run()
