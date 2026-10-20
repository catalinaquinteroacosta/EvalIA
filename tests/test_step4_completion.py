"""Focal regression for persisted completion and safe error delivery."""
import sqlite3
import json
from types import SimpleNamespace
from backend.integrated_evaluation import refresh_experiment_status

def test_completion_requires_all_models_turns_and_accepts_complete_na_review(tmp_path):
    path=tmp_path/'db.sqlite'
    con=sqlite3.connect(path)
    con.executescript('CREATE TABLE experiments(id INTEGER PRIMARY KEY,status TEXT,updated_at TEXT);CREATE TABLE experiment_models(experiment_id INTEGER,ai_model_id INTEGER);CREATE TABLE responses(id INTEGER,experiment_id INTEGER,ai_model_id INTEGER,turn_id INTEGER);CREATE TABLE conversation_turns(id INTEGER,turn_number INTEGER);CREATE TABLE evaluations(id INTEGER,response_id INTEGER);CREATE TABLE evaluation_reviews(id INTEGER,response_id INTEGER,result_json TEXT);INSERT INTO experiments VALUES(1,"created",NULL);INSERT INTO experiment_models VALUES(1,1);INSERT INTO experiment_models VALUES(1,2);INSERT INTO conversation_turns VALUES(1,1);INSERT INTO conversation_turns VALUES(2,2);')
    con.commit();con.close()
    def connect():
        c=sqlite3.connect(path);c.row_factory=sqlite3.Row;return c
    main=SimpleNamespace(get_connection=connect,_read_experiment_snapshot=lambda eid:{'turns':[{'id':1},{'id':2}]})
    def state():
        c=connect();s=c.execute('SELECT status FROM experiments').fetchone()[0];c.close();return s
    refresh_experiment_status(main,1);assert state()=='created'
    c=connect();c.executemany('INSERT INTO responses VALUES(?,?,?,?)',[(1,1,1,1),(2,1,1,2),(3,1,2,1),(4,1,2,2)])
    c.executemany('INSERT INTO evaluations VALUES(?,?)',[(1,1),(2,2),(3,3)]);c.commit();c.close()
    refresh_experiment_status(main,1);assert state()=='in_progress'
    c=connect();c.execute('INSERT INTO evaluation_reviews VALUES(1,4,?)',(json.dumps({'evaluation_state':'review_required'}),));c.commit();c.close()
    refresh_experiment_status(main,1);assert state()=='in_progress'
    c=connect();c.execute('INSERT INTO evaluation_reviews VALUES(2,4,?)',(json.dumps({'evaluation_state':'complete'}),));c.commit();c.close()
    refresh_experiment_status(main,1);assert state()=='evaluated'

def test_runtime_error_is_safe_http_503_without_loss(monkeypatch):
    import importlib.util
    from pathlib import Path
    spec=importlib.util.spec_from_file_location('platform_test',Path(__file__).parent/'test_step4_platform.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    from backend import validation_runtime as rt
    main,replay=rt.configure(rt.OUTPUT/'verified/application.db')
    workflow=rt.read(rt.OUTPUT/'MANUAL_WORKFLOW.json')
    class Stop:
        def __init__(self,*args,**kwargs):pass
        def evaluate_response(self,*args):raise RuntimeError('simulated uncertain transport, never transmitted')
    previous=main.app.state.evaluation_dependencies
    configured=dict(previous,runner_factory=Stop,allowed_experiment_ids=frozenset([workflow['experiment_id']]))
    monkeypatch.setattr(main.app.state,'evaluation_dependencies',configured)
    before=len(replay.used)
    status,payload=helper.request((main,replay),'POST',f"/api/responses/{workflow['recoverable_response_ids'][0]}/evaluate")
    assert status==503 and payload['detail']['automatic_retry'] is False
    assert len(replay.used)==before
    status,data=helper.request((main,replay),'GET',f"/api/experiments/{workflow['experiment_id']}/results")
    assert status==200 and len(data['results'])==25
