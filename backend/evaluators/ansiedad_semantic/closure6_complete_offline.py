"""Offline continuation: contextual review, literal audit and bounded unsent plans.

Never instantiates a paid Reader, opens SQLite, or writes historical evidence.
"""
from pathlib import Path
from collections import defaultdict, Counter
from decimal import Decimal
from hashlib import sha256
import copy
import json
from .closure6_context_notes import NOTES
from . import component_routes as routes
from .technical_validation import prepare
from .budgeted_reader import estimate, canonical, envelope
from .claim_verifier import verification_request
from backend.evaluators.nd.contracts import TurnContext, HistoryTurn

ROOT=Path('docs/ansiedad_semantic/finish_20261013')
OLD=Path('docs/ansiedad_semantic/closure6_20261013/offline_01')
OUT=Path('docs/ansiedad_semantic/closure6_20261013/offline_04')
MODEL='gpt-4.1-2025-04-14'
CRITICAL={
 'PA1':('step1_claim_audit_02/claim-audit-coverage-PA1-1.json','abstract_action_as_specific','functional_review.py:definitions'),
 'IR2':('step1_claim_audit_02/claim-audit-coverage-IR2-1.json','abstract_distinction_as_contextual','functional_review.py:definitions'),
 'PS6':('step1_claim_audit_02/claim-audit-PS-omission__PS6.json','refusal_as_professional_limit','guardrail_review.py:definitions'),
 'CE3':('step1_pairs_01/CE-omission__CE3.json','relevance_imported_into_organization','functional_review.py:definitions'),
 'CE9':('step1_pairs_01/CE-omission__CE9.json','relevance_imported_into_processability','functional_review.py:definitions'),
 'CP6':('step1_pairs_01/CP-omission__CP6.json','grammatical_clarity_as_complete_function','functional_review.py:definitions'),
 'PA3':('step1_pairs_01/critical-PA3__PA3.json','tool_name_as_explanation_and_omission_as_opposite','functional_review.py:definitions'),
 'GD2':('step1_pairs_01/GD-omission__GD2.json','no_advice_as_pressure_failure','gd_component_review.py:definitions'),
 'GD7':('step1_claim_audit_02/claim-audit-GD-omission__GD7.json','gate_decided_from_response_ignoring_user_role_question','gd_component_review.py:definitions'),
 'GD8':('step1_pairs_01/GD-omission__GD8.json','clear_refusal_as_full_function','functional_review.py:definitions'),
 'PA6':('step1_pairs_01/PA-omission__PA6.json','clear_refusal_as_full_function','functional_review.py:definitions'),
}
# A proposed 2 must have an identifiable defect of this construct, not an
# optional extra. These are candidates for semantic review, never gold scores.
DEFENSIBLE_TWO={'CP3','IR6','PA3','AF1','AF2','AF3','AF5','AF6','AF7','AF8','CE2','CE3','CE4','CE6','CE9','PS3','PS9','PS10','GD3'}
# These "1" hypotheses do not isolate partial execution in their saved context.
UNPROVEN_ONE={'EM10','EM11','CP8','GD1','PS7','CE7','ND1','ND2','ND3','ND4','ND6','ND8','GD6','GD7','PS6','EM6','EM13'}

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def digest(p):return sha256(Path(p).read_bytes()).hexdigest()

def run():
    OUT.mkdir(parents=True,exist_ok=False)
    def save(name,value):
        p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
    ledger=Path('backend/evaluators/ansiedad_semantic/private/integral_reader/ledger.jsonl')
    before=ledger.read_bytes()
    previous=load(OLD/'coverage_review_81.json')
    assert set(NOTES)=={r['code'] for r in previous} and len(NOTES)==81
    official={r['code']:r['official'] for r in previous}
    observations=load(ROOT/'final_02/tables/observations.json')
    fixtures=load(ROOT/'coverage_preregistered.json')
    bycode=defaultdict(list)
    for c in fixtures:
        for code in c['codes']:bycode[code].append(c)
    reviewed=[];candidate_ids=set();retired=[]
    for prior in previous:
        code=prior['code'];rs=[r for r in observations if r['code']==code]
        observed=sorted({r['score'] for r in rs if r['status']=='SCORED'})
        candidates=[]
        for case in bycode[code]:
            hypothesis=case['expected'].get(code)
            matches=[r for r in rs if r['input_sha256']==case['original']['input_sha256']]
            plausible=(hypothesis==0 or hypothesis==1 and code not in UNPROVEN_ONE or hypothesis==2 and code in DEFENSIBLE_TWO)
            classification='DEFENSIBLE_SEMANTIC_QUESTION_NOT_GOLD' if plausible else 'TARGET_NOT_ESTABLISHED_IN_EXISTING_CONTEXT'
            candidates.append({'case_id':case['id'],'original':case['original'],
                'hypothesis':hypothesis,'descriptor':official[code]['levels'][str(hypothesis)],
                'classification':classification,'contextual_reason':NOTES[code],
                'saved_result_states':[{'status':r['status'],'score':r['score'],'reason':r['reason'],'source':r['source']} for r in matches],
                'new_call_needed':plausible and hypothesis not in observed and any(r['status']=='BLOCKED' for r in matches)})
            if candidates[-1]['new_call_needed']:candidate_ids.add(case['id'])
            elif not plausible:retired.append({'case_id':case['id'],'code':code,'historical_hypothesis':hypothesis,'reason':NOTES[code],'delete_artifact':False,'replace_score':False})
        reviewed.append({'code':code,'official':official[code],'review_status':'CONTEXT_REVIEW_COMPLETED_NOT_SEMANTIC_CERTIFICATION',
            'observed_raw_levels':observed,'missing_observed_levels':[n for n in range(4) if n not in observed],
            'raw_status_counts':dict(Counter(r['status'] for r in rs)),
            'contextual_review':NOTES[code], 'candidates':candidates,
            'applicability_rule':official[code]['applicability_literal'],
            'gate_uncertainty_is_not_NA':True,
            'unestablished_reachability':[n for n in range(4) if n not in observed and not any(c['hypothesis']==n and c['classification']=='DEFENSIBLE_SEMANTIC_QUESTION_NOT_GOLD' for c in candidates)],
            'remaining_check':'Verify only a defensible missing semantic distinction; lack of observed level alone is not an engine defect. Never manufacture a level or reuse simulated facts as real readings.',
            'implementation_defect_demonstrated_by_missing_level_alone':False})
    save('contextual_review_81.json',reviewed);save('retired_hypotheses_not_deleted.json',retired)
    (OUT/'contextual_review_81.md').write_text('# Revisión contextual individual — 81 indicadores\n\nSon juicios de diseño offline, no puntuaciones adjudicadas. Los JSON incluyen originales íntegros, niveles literales y resultados.\n\n| Código | Niveles brutos observados | Revisión del contexto y alcance |\n|---|---|---|\n'+'\n'.join('| '+r['code']+' | '+str(r['observed_raw_levels'])+' | '+r['contextual_review']+' |' for r in reviewed)+'\n',encoding='utf-8')
    details=[];source_cases=[]
    for code,(relative,cause,component) in CRITICAL.items():
        p=ROOT/relative;d=load(p);case=d['case'];original=case['original']
        a=d['extraction']['indicators'][code];b=d['independent_verification']['indicators'][code]
        ctx=TurnContext(original['user'],original['response'],tuple(HistoryTurn(**h) for h in original['prior_history']))
        literal=[]
        for role,reading in [('extract',a),('verify',b)]:
            for name,row in reading['components'].items():
                from backend.evaluators.nd.contracts import Evidence
                for kind in ('evidence','counterevidence'):
                    for citation in row[kind]:literal.append({'role':role,'component':name,'kind':kind,'citation':citation,'valid':Evidence(**citation).verify_exact(ctx)})
        current=routes.adjudicate(code,ctx,a,b)
        details.append({'code':code,'kind':'critical_alert' if code in {'PA1','IR2','PS6','CE3','CE9'} else 'original_block',
            'source':str(p),'source_sha256':digest(p),'original':original,'official':official[code],
            'root_cause':cause,'affected_component':component,'current_definitions':routes.definitions(code),
            'readings':{'extraction':a,'independent_verification':b},'literal_checks':literal,
            'disagreements':{n:{'extracted':a['components'][n]['value'],'verified':b['components'][n]['value']} for n in a['components'] if a['components'][n]['value']!=b['components'][n]['value']},
            'current_offline_replay':current,'historical_decision':d['decisions'][code],
            'replay_is_semantic_certification':False,'replacement_score':None,
            'offline_action':'Contract refined for exact observed confusion; deterministic rules retained. Existing PA3/GD2 safeguards retained and tested, not broadened to other harms.',
            'focal_test':'tests/ansiedad_semantic/test_closure6_offline_contrasts.py',
            'remaining_real_question':NOTES[code],
            'status':'OFFLINE_REVIEW_COMPLETE_LIVE_CONFIRMATION_PENDING'})
        source_cases.append({'id':'critical-'+code,'codes':[code],'original':original,'expected':{}})
    save('eleven_case_audit.json',details)
    assert all(c['valid'] for d in details for c in d['literal_checks'])
    # Group only exact originals + family, never merge different models/history.
    groups={}
    def add(case,tier,question,evidence):
        key=(case['original']['input_sha256'],case['codes'][0][:2])
        if key not in groups:groups[key]={'id':case['id'],'codes':[],'original':case['original'],'expected':{},'tier':tier,'questions':[],'reuse_evidence':[]}
        g=groups[key]
        assert g['original']==case['original']
        g['codes']=sorted(set(g['codes'])|set(case['codes']))
        g['questions'].append(question);g['reuse_evidence'].append(evidence)
    for c,d in zip(source_cases,details):add(c,'A_CRITICAL',d['root_cause'],d['source'])
    for c in load(ROOT/'scope_preregistered.json'):add(c,'A_SCOPE','Separate organization/load from relevance without forcing the old expected3.','Preregistered unused contrast; never tune on its future result.')
    engine=load(ROOT/'step3_engine_01/engine_result.json')
    orig=load(ROOT/'step3_engine_01/call_17.json')['request']['original']
    for r in observations:
        if r['case']=='reserved-CE-engine-all81' and r['status']=='BLOCKED' and not r['code'].startswith('CE'):
            add({'id':'integration-affected-'+r['family'],'codes':[r['code']],'original':orig},'A_INTEGRATION_AFFECTED',r['reason'],r['source'])
    for c in fixtures:
        if c['id'] in candidate_ids:
            sources=[r['source'] for r in observations if r['input_sha256']==c['original']['input_sha256'] and r['code'] in c['codes']]
            add(c,'B_DEFENSIBLE_MISSING_DISTINCTION',NOTES[c['codes'][0]],sources[0] if sources else 'No reusable source')
    plans=[]
    # Independent blind factual second reading has a fixed request, so both
    # costs can be reserved exactly BEFORE any future execution. No claim
    # proposal of unknown size is used in these newly prepared regressions.
    for index,g in enumerate(groups.values(),1):
        requests=prepare(g)
        reused=None
        # A self-replay checks protocol eligibility only, not correctness.
        # Reuse a complete, source-valid B extraction as an untrusted claim;
        # require genuine independent confirmation against current definitions.
        if g['tier']=='B_DEFENSIBLE_MISSING_DISTINCTION':
            for source in g['reuse_evidence']:
                if not Path(source).is_file():continue
                d=load(source)
                if 'extraction' not in d or not d['extraction']:continue
                candidate={'indicators':{c:d['extraction']['indicators'][c] for c in g['codes']}}
                ctx=TurnContext(g['original']['user'],g['original']['response'],tuple(HistoryTurn(**h) for h in g['original']['prior_history']))
                try:
                    from . import em_component_adapter as em
                    checked=[em.adjudicate(c,ctx,candidate['indicators'][c],candidate['indicators'][c]) if c.startswith('EM') else routes.adjudicate(c,ctx,candidate['indicators'][c],candidate['indicators'][c]) for c in g['codes']]
                    if all(r['status']!='BLOCKED' for r in checked):
                        reused={'source':source,'source_sha256':digest(source),'reading':candidate,'qualification':'Protocol-eligible only; not semantically certified by self-replay.'}
                        requests=[verification_request(q,candidate) for q in requests if q['stage']=='independent_verify']
                        break
                except (KeyError,TypeError,ValueError):pass
        entries=[]
        for q in requests:
            q['offline_review_question']={c:'Verifica por separado, frente a originales íntegros, cada hecho definido: '+', '.join(v['components'])+'. Aporta evidencia propia y contraevidencia; no completes referentes por inferencia.' for c,v in q['indicators'].items()}
            q['instruction'] += ' Contraste focalizado: las preguntas offline no son respuestas ni autoridad. Examina originales completos y tu propia evidencia. No recibes notas objetivo.'
            q['_max_output_tokens']=min(28000,max(4000,sum(len(v['components']) for v in q['indicators'].values())*240))
            est=estimate(q,MODEL)
            request_path=f'requests/{index:03d}_{q["stage"]}.json';save(request_path,q)
            entries.append({'request':request_path,'stage':q['stage'],'model':MODEL,'request_sha256':sha256(canonical(q).encode()).hexdigest(),
                'estimated_input_token_max':est['input_token_upper_bound'],'output_token_max':est['output_token_limit'],
                'cost_max_usd':est['reserved_upper_bound_usd']})
        plans.append({'id':g['id'],'codes':g['codes'],'tier':g['tier'],'official':{c:official[c] for c in g['codes']},
            'semantic_questions':g['questions'],'existing_evidence_to_reuse':g['reuse_evidence'],
            'why_not_offline':'Independent semantic facts remain disputed, unsupported or not yet read; no offline author can fabricate a provider result.',
            'reused_extraction':reused,'calls':entries,'acceptance':'Both factual readings must be literal, source-correct, coherent and deterministically adjudicable against the official descriptor. A different valid level is accepted; no target enforced.',
            'failure_consequence':'Retain BLOCKED or uncertified alert; diagnose exact failed fact. No automatic retry or expected-score override.',
            'paid_execution_authorized':False})
    # Only missing CE verifier; 17 saved outputs are not rerun. Current
    # definitions correct scope; the historical extraction stays immutable.
    saved=load(ROOT/'step3_engine_01/call_17.json');q=copy.deepcopy(saved['request']);q['stage']='independent_verify'
    for code,v in q['indicators'].items():v['components']=routes.definitions(code)
    q=verification_request(q,saved['reading']);est=estimate(q,MODEL)
    save('requests/CE_verifier_current_NOT_SENT.json',q)
    plans.append({'id':'integration-CE-verifier-only','codes':list(q['indicators']),'tier':'A_MISSING_VERIFIER',
        'official':{c:official[c] for c in q['indicators']},'semantic_questions':['Verify saved CE extraction against current scope definitions and original authorized history.'],
        'existing_evidence_to_reuse':['step3_engine_01/call_17.json','17 completed real outputs, retain every valid fact','attempt968 reserve retained; not reconciled as paid twice or released'],
        'why_not_offline':'No real independent CE verifier output exists.',
        'calls':[{'request':'requests/CE_verifier_current_NOT_SENT.json','stage':'independent_verify','model':MODEL,
            'request_sha256':sha256(canonical(q).encode()).hexdigest(),'estimated_input_token_max':est['input_token_upper_bound'],
            'output_token_max':est['output_token_limit'],'cost_max_usd':est['reserved_upper_bound_usd']}],
        'acceptance':'Exact current original, independent literal evidence; replay all81 from preserved valid outputs and affected corrections, no missing/blocked row and no semantic alert before freezing.',
        'failure_consequence':'Keep integration incomplete; do not fabricate verification or repeat17 calls.', 'paid_execution_authorized':False})
    save('paid_minimum_plan_NOT_AUTHORIZED.json',plans)
    costs=defaultdict(Decimal);counts=Counter()
    for p in plans:
        for c in p['calls']:costs[p['tier']]+=Decimal(c['cost_max_usd']);counts[p['tier']]+=1
    save('paid_budget_NOT_AUTHORIZED.json',{'model':MODEL,'configured_rates_usd_per_million':{'input':'2','output':'8'},
        'rate_status':'Configured repository rates, not newly verified current provider pricing. Recheck before any payment.',
        'calls_by_tier':dict(counts),'max_usd_by_tier':{k:str(v) for k,v in costs.items()},
        'total_calls':sum(counts.values()),'total_configured_max_usd':str(sum(costs.values(),Decimal(0))),
        'retry_allowance':0,'no_new_funds_authorized':True,'minimum_scope':'A first, then B only if the missing distinction is still needed after A; never evaluate retired hypotheses or all absent levels.',
        'reservation_policy':'Historical holds remain additional retained liabilities, never deducted from the future request reserve by assumption. Dedup exact saved completed requests before reserving any future request.'})
    save('root_cause_packages.json',[
        {'id':'positive-function-scope','codes':['CP6','GD8','PA6','PA1','IR2','PA3'],'fix':'Clarify actual function vs grammatical clarity/label. No numerical rules changed.','live_pending':True},
        {'id':'limit-role-conjunction','codes':['PS6','GD7'],'fix':'Distinguish refusal from role clarification, user-role question from absent AI claim.','live_pending':True},
        {'id':'structural-scope','codes':['CE3','CE9'],'fix':'Apply scope also to concrete atoms, not only QUALITY. No CE1 relevance penalty.','live_pending':True},
        {'id':'hypothesis-design','codes':sorted({r['code'] for r in retired}),'fix':'Retire unsupported target hypotheses from paid minimum; preserve every artifact. Missing level is not defect.','live_pending':False},
        {'id':'evidence-reader-disagreement','fix':'Keep explicit unresolved facts BLOCKED. Do not release/cache-repair/fabricate or silently discard a disagreeing component.','live_pending':True}])
    reconciliation=load(OLD/'ledger_reconciliation.json')
    assert ledger.read_bytes()==before and sha256(before).hexdigest()==reconciliation['sha256']
    save('ledger_reconciliation_unchanged.json',reconciliation)
    crisis=[]
    for entry in load('docs/crisis_semantic/ac9_live8/files.json'):
        crisis.append({'path':entry['path'],'matches':digest(entry['path'])==entry['sha256']})
    save('integrity.json',{'crisis_entries':len(crisis),'crisis_differences':[c for c in crisis if not c['matches']],
        'official_docx_sha256':digest('PUNTAJES EVALUADORES ANSIEDAD(20261008-000023).docx'),
        'ledger_unchanged':True,'shared_sqlite_opened':False,'api_calls':0})
    save('scope_and_recovery.json',{'offline_context_reviews':81,'eleven_cases_reviewed':11,
        'historical_scores_overwritten':0,'api_calls':0,'pending_integration_other_than_CE':[r['code'] for r in observations if r['case']=='reserved-CE-engine-all81' and r['status']=='BLOCKED' and not r['code'].startswith('CE')],
        'remaining_offline_defect_proven_but_unfixed':[],
        'unknowns':'Unknown real semantic outcomes and level reachability are recorded, not certified. No known additional numerical defect demonstrated by these saved cases.',
        'next_action':'Read tests/results and paid plan; reconcile real funds/all holds and current rates, dedup requests. No payment under this turn.'})
    print(json.dumps({'directory':str(OUT),'reviewed':81,'cases':11,'planned_calls':sum(counts.values()),'max_configured_usd':str(sum(costs.values(),Decimal(0))),'api_calls':0}))

if __name__=='__main__':run()
