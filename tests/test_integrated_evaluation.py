"""Focused compatibility/financial/history guards, not semantic certification."""
from copy import deepcopy
from types import SimpleNamespace
import sqlite3
import pytest
from fastapi import HTTPException
from backend.integrated_evaluation import compatible_result,evaluate_response
from backend.evaluation_engine import EvaluationEngine
from backend.evaluators.transversal_candidate_v1.integration_runner import aggregate_v2

def canonical(rubric='crisis',status='SCORED'):
    engine=EvaluationEngine(rubric)
    rows=[dict(code=c,status=status,score=2 if status=='SCORED' else None,applicable=status=='SCORED',reason='Controlled fixture.') for c in engine.indicators_by_code]
    return dict(rubric_type=rubric,engine='controlled_fixture',turn_number=1,indicator_results=rows,
        aggregation=aggregate_v2(rows,engine.indicator_to_criterion))

@pytest.mark.parametrize('rubric,count',[('crisis',104),('ansiedad_depresion',81)])
def test_complete_v2_compatible_without_input_mutation(rubric,count):
    selected=canonical(rubric);original=deepcopy(selected)
    internal,public,complete=compatible_result(selected)
    assert complete and selected==original
    assert public['global_result']['percentage']==selected['aggregation']['global_v2']==66.67
    assert len(public['indicator_details'])==count
    assert all(c['percentage']==66.67 for c in public['criteria'])
    assert public['validated_audit']==selected

def test_all_na_stays_non_numeric():
    internal,public,complete=compatible_result(canonical(status='N/A'))
    assert complete and public['global_result']['percentage'] is None
    assert public['global_result']['classification']=='No evaluable'
    assert all(r['score'] is None and r['applicable'] is False for r in public['indicator_details'])

def test_review_not_na_not_zero_and_coverage_is_applicability():
    selected=canonical();selected['indicator_results'][0].update(status='BLOCKED',score=None,applicable=True)
    engine=EvaluationEngine('crisis');selected['aggregation']=aggregate_v2(selected['indicator_results'],engine.indicator_to_criterion)
    internal,public,complete=compatible_result(selected)
    assert not complete and public['global_result']['percentage'] is None
    assert public['global_result']['applicable_indicators']==104
    assert public['global_result']['not_applicable_indicators']==0
    assert public['indicator_details'][0]['status']=='BLOCKED'
    assert public['indicator_details'][0]['applicable'] is True and public['indicator_details'][0]['score'] is None
    assert all(c['coverage']['total_indicators']==c['total_indicators'] for c in public['criteria'])

def unsaved_main():
    def absent(_):raise HTTPException(status_code=404,detail='No saved result')
    return SimpleNamespace(_get_response_context=lambda _:dict(experiment_id=1,scenario_code='TEST',scenario_id=1),
        _load_saved_evaluation=absent,_require_experiment_snapshot_current=lambda *a:{},app=SimpleNamespace(state=SimpleNamespace()))

def test_no_implicit_paid_reader():
    with pytest.raises(HTTPException) as e:evaluate_response(unsaved_main(),1)
    assert e.value.status_code==503 and 'autorizado' in e.value.detail

def test_historical_new_evaluation_guard_precedes_reader():
    main=unsaved_main()
    def missing(*a):raise ValueError('Historical snapshot missing')
    main._require_experiment_snapshot_current=missing
    with pytest.raises(HTTPException) as e:evaluate_response(main,1)
    assert e.value.status_code==409

def test_existing_result_is_returned_exactly_without_reader():
    main=unsaved_main();legacy={'kept':'byte-equivalent JSON value'}
    main._load_saved_evaluation=lambda _:dict(evaluator_type='historical',evaluation_id=9,result=legacy)
    result=evaluate_response(main,1)
    assert result['historical_preserved'] and result['result'] is legacy

def test_race_guard_preserves_existing_json(tmp_path,monkeypatch):
    from backend import main
    path=tmp_path/'app.db'
    db=sqlite3.connect(path);db.execute('CREATE TABLE evaluations(id INTEGER PRIMARY KEY,response_id INTEGER,result_json TEXT)')
    db.execute("INSERT INTO evaluations VALUES (1,1,'unchanged')");db.commit();db.close()
    def connection():
        db=sqlite3.connect(path);db.row_factory=sqlite3.Row;return db
    monkeypatch.setattr(main,'get_connection',connection)
    internal={'evaluation':{'global_result':{'coverage':{}}},'indicator_results':[]}
    with pytest.raises(HTTPException) as e:main._save_evaluation_result(1,internal,{},preserve_existing=True)
    assert e.value.status_code==409
    with connection() as db:assert db.execute('SELECT result_json FROM evaluations').fetchone()[0]=='unchanged'
