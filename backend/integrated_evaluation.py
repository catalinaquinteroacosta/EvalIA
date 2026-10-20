"""Composition/compatibility only; validated family engines remain immutable."""
from copy import deepcopy
import json
import sys
from pathlib import Path
# Frozen CRISIS modules use their historical top-level package identity.
_evaluators=str(Path(__file__).resolve().parent/'evaluators')
if _evaluators not in sys.path:sys.path.insert(0,_evaluators)
from fastapi import HTTPException
from backend.evaluators.transversal_candidate_v1.adenda_v11_runner import IntegrationRunner
from backend.evaluators.transversal_candidate_v1.adenda_qualified_v11_provider import AdendaV11Provider
from backend.evaluation_engine import EvaluationEngine
from backend.evaluators.criterion_presenter import CriterionPresenter
from contextvars import ContextVar
from contextlib import contextmanager

_request_dependencies=ContextVar('evalia_authorized_job_dependencies',default=None)

def evaluation_dependencies(main):
    return _request_dependencies.get() or getattr(main.app.state,'evaluation_dependencies',None)

@contextmanager
def using_dependencies(dependencies):
    token=_request_dependencies.set(dependencies)
    try:yield
    finally:_request_dependencies.reset(token)


def authoritative_record(main, raw):
    context=main._build_evaluation_context(raw)
    if context.experiment_id!=int(raw['experiment_id']) or context.model_name!=raw['model_name']:
        raise ValueError('authoritative_context_identity_mismatch')
    conversation=str(context.experiment_id)+':'+context.scenario_code
    return dict(rubric_type=context.rubric_type,model=context.model_name,turn=int(raw['turn_number']),conversation=conversation,
        originals=[dict(conversation=conversation,model=context.model_name,turn=t.turn_number,user=t.user_message,response=t.ai_response) for t in context.turns])


def compatible_result(selected):
    """Map canonical rows to existing tables; never rerun a family scorer."""
    rubric=selected['rubric_type'];engine=EvaluationEngine(rubric)
    native=selected['indicator_results']
    if len(native)!=len(engine.indicators_by_code) or {r['code'] for r in native}!=set(engine.indicators_by_code):
        raise ValueError('validated_indicator_inventory_mismatch')
    complete=all(r['status'] in ('SCORED','N/A') for r in native)
    indicators=[]
    for row in native:
        code=row['code'];meta=engine.indicators_by_code[code]
        if row['status']=='SCORED' and (type(row['score']) is not int or row['score'] not in range(4)):
            raise ValueError('invalid_canonical_score')
        if row['status']!='SCORED' and row['score'] is not None:raise ValueError('invalid_unscored_number')
        applicable=True if row['status']=='SCORED' else False if row['status']=='N/A' else row.get('applicable')
        reason=row.get('reason') or row.get('technical_cause') or row.get('justification') or 'Componentes reconciliados por el motor vigente.'
        indicators.append(dict(indicator_code=code,criterion_code=engine.indicator_to_criterion[code],
            applicable=applicable,score=row['score'],justification=reason,type=meta['type'],criticality=meta['criticality'],
            priority=meta.get('priority','normal'),critical_failure=False,status=row['status']))
    if complete:
        evaluation=engine.validate_evaluation({'indicators':indicators})
        # The selected validated V2 aggregation is authoritative, including all-N/A.
        value=selected['aggregation']['global_v2']
        evaluation['global_result']['percentage']=value
        if value is None:
            evaluation['global_result']['classification']='No evaluable'
            evaluation['global_result']['classification_before_critical_rules']='No evaluable'
            evaluation['executive_summary']='No hay indicadores puntuables en esta evaluación.'
        else:
            label=engine.classify_percentage(value)
            evaluation['global_result']['classification_before_critical_rules']=label
            evaluation['global_result']['classification']=engine._apply_critical_limits(original_classification=label,critical_alerts=evaluation['critical_alerts'])
    else:
        applicable_count=sum(r['status']=='SCORED' or r.get('applicable') is True for r in native)
        na=sum(r['status']=='N/A' for r in native)
        cov=engine._calculate_coverage(applicable_count=applicable_count,total_count=len(native))
        evaluation=dict(rubric_type=rubric,rubric_name=engine.rubric['name'],rubric_version=engine.rubric['version'],
            global_result=dict(percentage=None,classification='En revisión',classification_before_critical_rules='En revisión',
                applicable_indicators=applicable_count,not_applicable_indicators=na,total_indicators=len(native),coverage=cov),
            criteria=[],strengths=[],improvement_opportunities=[],critical_alerts=[],executive_summary='Evaluación en revisión; no se calcula un global.',
            internal_detail={'indicators':indicators})
        for criterion in engine.rubric['criteria']:
            local=[r for r in indicators if r['criterion_code']==criterion['code']]
            evaluation['criteria'].append(dict(criterion_code=criterion['code'],criterion_name=criterion['name'],order=criterion.get('order',0),
                score_0_to_3=None,percentage=None,classification='En revisión',total_score=None,maximum_score=None,
                applicable_indicators=sum(r['applicable'] is True for r in local),not_applicable_indicators=sum(r['status']=='N/A' for r in local),
                total_indicators=len(local),coverage=engine._calculate_coverage(applicable_count=sum(r['applicable'] is True for r in local),total_count=len(local)),has_critical_failure=False,critical_failure_count=0))
    internal=dict(evaluation=evaluation,indicator_results=[{**r,'indicator_code':r['code']} for r in native],validated_audit=selected)
    public=CriterionPresenter(rubric).present_turn(turn_number=selected['turn_number'],evaluation_result=evaluation)
    public.update(engine_version=selected['engine'],evaluation_state='complete' if complete else 'review_required',
        validated_audit=selected,indicator_results=deepcopy(native),indicator_details=deepcopy(evaluation['internal_detail']['indicators']))
    return internal,public,complete


def save_review(main,response_id,public):
    """Append unresolved JSON separately; legacy NOT NULL score columns stay intact."""
    connection=main.get_connection()
    try:
        connection.execute('CREATE TABLE IF NOT EXISTS evaluation_reviews (id INTEGER PRIMARY KEY, response_id INTEGER NOT NULL REFERENCES responses(id), engine_version TEXT NOT NULL, result_json TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')
        connection.execute('BEGIN IMMEDIATE')
        previous=connection.execute('SELECT id,result_json FROM evaluation_reviews WHERE response_id=? ORDER BY id DESC LIMIT 1',(response_id,)).fetchone()
        # Compare the persisted JSON representation (native audit may contain
        # tuples which become lists on disk), without altering its values.
        if previous and json.loads(previous['result_json'])==json.loads(json.dumps(public,ensure_ascii=False)):
            connection.commit()
            return previous['id']
        cursor=connection.execute('INSERT INTO evaluation_reviews(response_id,engine_version,result_json) VALUES (?,?,?)',
            (response_id,public['engine_version'],json.dumps(public,ensure_ascii=False)))
        connection.commit();return cursor.lastrowid
    except BaseException:
        connection.rollback()
        raise
    finally:connection.close()


def load_review(main,response_id):
    connection=main.get_connection()
    try:
        if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='evaluation_reviews'").fetchone():return None
        row=connection.execute('SELECT id,result_json,created_at FROM evaluation_reviews WHERE response_id=? ORDER BY id DESC LIMIT 1',(response_id,)).fetchone()
        if not row:return None
        result=json.loads(row['result_json'])
        return dict(review_id=row['id'],response_id=response_id,result=result,created_at=row['created_at'],review_required=result.get('evaluation_state')=='review_required')
    finally:connection.close()


def evaluate_response(main,response_id):
    from contextlib import nullcontext
    dependencies=evaluation_dependencies(main) or {}
    with dependencies.get('evaluation_lock',nullcontext()):
        return _evaluate_response(main,response_id)


def refresh_experiment_status(main, experiment_id):
    """Completion is based on persisted turn evaluations, without inventing a longitudinal score."""
    snapshot=main._read_experiment_snapshot(experiment_id)
    turns={int(t['id']) for t in snapshot.get('turns',[])}
    connection=main.get_connection()
    try:
        models={r['ai_model_id'] for r in connection.execute('SELECT ai_model_id FROM experiment_models WHERE experiment_id=?',(experiment_id,))}
        rows=connection.execute('SELECT responses.id, responses.ai_model_id, conversation_turns.turn_number, evaluations.id AS evaluation_id FROM responses JOIN conversation_turns ON conversation_turns.id=responses.turn_id LEFT JOIN evaluations ON evaluations.response_id=responses.id WHERE responses.experiment_id=?',(experiment_id,)).fetchall()
        complete=set()
        for row in rows:
            identity=(row['ai_model_id'],row['turn_number'])
            if row['ai_model_id'] not in models or row['turn_number'] not in turns:continue
            if row['evaluation_id'] is not None:complete.add(identity);continue
            if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='evaluation_reviews'").fetchone():
                review=connection.execute('SELECT result_json FROM evaluation_reviews WHERE response_id=? ORDER BY id DESC LIMIT 1',(row['id'],)).fetchone()
                if review and json.loads(review['result_json']).get('evaluation_state')=='complete':complete.add(identity)
        expected={(model,turn) for model in models for turn in turns}
        state='evaluated' if expected and complete==expected else 'in_progress' if rows else 'created'
        connection.execute('UPDATE experiments SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?',(state,experiment_id))
        connection.commit()
    except BaseException:
        connection.rollback();raise
    finally:connection.close()


def _evaluate_response(main,response_id):
    raw=main._get_response_context(response_id)
    # Existing records retain their exact historical evaluator and scores.
    try:
        saved=main._load_saved_evaluation(response_id)
    except HTTPException as error:
        if error.status_code!=404:raise
    else:
        return dict(status='already_evaluated',mode=saved['evaluator_type'],response_id=response_id,
            evaluation_id=saved['evaluation_id'],conversation_evaluation_id=None,result=saved['result'],historical_preserved=True)
    review=load_review(main,response_id)
    if review and review['result'].get('evaluation_state')=='complete':
        return dict(status='already_evaluated',mode=review['result'].get('engine_version'),response_id=response_id,
            evaluation_id=None,review_id=review['review_id'],conversation_evaluation_id=None,result=review['result'],historical_preserved=True)
    try:main._require_experiment_snapshot_current(int(raw['experiment_id']),raw['scenario_code'],int(raw['scenario_id']))
    except ValueError as error:raise HTTPException(status_code=409,detail=str(error)) from error
    # Semantic transports are server-side dependencies, never accepted from HTTP.
    dependencies=evaluation_dependencies(main)
    if dependencies is None:
        raise HTTPException(status_code=503,detail='El motor vigente está conectado; falta configurar un lector con presupuesto API autorizado. No se consumió API.')
    allowed=dependencies.get('allowed_experiment_ids')
    if allowed is not None and int(raw['experiment_id']) not in allowed:
        raise HTTPException(status_code=403,detail='Experimento fuera del presupuesto autorizado.')
    record=authoritative_record(main,raw)
    provider=dependencies.get('crisis_provider')
    reader=dependencies.get('anxiety_reader')
    if (record['rubric_type']=='crisis' and provider is None) or (record['rubric_type']=='ansiedad_depresion' and reader is None):
        raise HTTPException(status_code=503,detail='Lector semántico autorizado no configurado para esta rúbrica.')
    try:
        runner_factory=dependencies.get('runner_factory',IntegrationRunner)
        selected=runner_factory(lambda _:record,crisis_provider=provider,anxiety_reader=reader,
            external_attestations=dependencies.get('external_attestations',()),resource_checks=dependencies.get('resource_checks',())).evaluate_response(response_id)
        selected['controlled_test_fixture']=dependencies.get('controlled_test_fixture') is True
        internal,public,complete=compatible_result(selected)
    except (ValueError,TypeError,KeyError) as error:raise HTTPException(status_code=422,detail=str(error)) from error
    except RuntimeError as error:
        if getattr(error,'batch_pending',False):
            raise HTTPException(status_code=202,detail=dict(status='batch_pending',response_id=response_id,
                pending_requests=len(error.keys),message='Evaluación Batch pendiente; no hay puntuación final ni resultados guardados.')) from None
        raise HTTPException(status_code=503,detail={
            'status':'evaluation_safely_stopped',
            'message':'Evaluación detenida. Las respuestas se conservan. Revisa autorización, presupuesto y recibos antes de reanudar; una transmisión incierta no se repite automáticamente.',
            'automatic_retry':False,
        }) from None
    if complete and public['global_result']['percentage'] is not None:
        evaluation_id=main._save_evaluation_result(response_id,internal,public,preserve_existing=True)
        # Store evaluator identity truthfully; existing records were returned above.
        connection=main.get_connection()
        try:
            connection.execute('UPDATE evaluations SET evaluator_type=?,evaluator_model=? WHERE id=?',
                (selected['engine'],getattr(provider,'model',None) if record['rubric_type']=='crisis' else dependencies.get('anxiety_model'),evaluation_id))
            connection.commit()
        finally:connection.close()
        review_id=None
    else:
        evaluation_id=None;review_id=save_review(main,response_id,public)
    refresh_experiment_status(main,int(raw['experiment_id']))
    return dict(status='evaluated' if complete else 'review_required',mode=selected['engine'],engine_version=selected['engine'],
        response_id=response_id,evaluation_id=evaluation_id,review_id=review_id,conversation_evaluation_id=None,
        evaluated_model=record['model'],turn_number=record['turn'],result=public)
