"""Official DOCX bank/version isolation; no inference or shared writes."""
import hashlib
import json
import sqlite3
from pathlib import Path
import pytest
from backend import main, prompt_loader

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT/'docs/economic_readers_step3_20261015'

@pytest.fixture
def private_bank(tmp_path, monkeypatch):
    original=EVIDENCE/'bank32/prior_bank/evalia.db'
    path=tmp_path/'private.db'
    source=sqlite3.connect(original); target=sqlite3.connect(path)
    source.backup(target); target.close(); source.close()
    def connection():
        db=sqlite3.connect(path); db.row_factory=sqlite3.Row; return db
    monkeypatch.setattr(main,'get_connection',connection)
    return connection

def test_all_190_are_literal_docx_and_legacy_rows_unchanged(private_bank):
    doc=json.loads((EVIDENCE/'corrections_02/SCENARIO_MASTER_READONLY.json').read_text(encoding='utf8'))
    manifest=json.loads((prompt_loader.BANKS_DIR/'MATRIZ-MAESTRA-20261016/MANIFEST.json').read_text(encoding='utf8'))
    assert hashlib.sha256(Path(doc['source']).read_bytes()).hexdigest()==manifest['source_sha256']
    assert len(manifest['paragraph_mapping'])==190
    for name in manifest['files']:
        code=Path(name).stem
        index=doc['paragraphs'].index(code)
        assert index<132
        assert main.get_prompt(code)['category']==doc['paragraphs'][index+1].strip()
    for mapping in manifest['paragraph_mapping']:
        code=mapping['code']; number=mapping['turn']
        expected='\n'.join(doc['paragraphs'][i] for i in mapping['docx_paragraphs'])
        prompt=main.get_prompt(code)
        assert prompt['turns'][number-1]['user']==expected
        assert main.get_scenario(code)['turns'][number-1]['user_message']==expected
    with private_bank() as db:
        prior=json.loads((EVIDENCE/'bank32/prior_bank/prior_rows.json').read_text(encoding='utf8'))
        for table,rows in prior.items():
            assert [dict(r) for r in db.execute(f'SELECT * FROM {table} ORDER BY rowid')]==rows

def test_all_38_new_snapshots_same_questions_for_five_models(private_bank):
    with private_bank() as db: models=[r['name'] for r in db.execute('SELECT name FROM ai_models WHERE active=1 ORDER BY name')]
    assert len(models)==5
    manifest=json.loads((prompt_loader.BANKS_DIR/'MATRIZ-MAESTRA-20261016/MANIFEST.json').read_text(encoding='utf8'))
    positions=0
    for name in manifest['files']:
        code=Path(name).stem
        result=main.create_experiment(main.ExperimentRequest(scenario_code=code,model_names=models))
        snapshot=main._load_experiment_snapshot(result['experiment_id'])
        assert snapshot['turns']==main.get_prompt(code)['turns']
        assert snapshot['bank_version']=='MATRIZ-MAESTRA-20261016'
        detail=main.get_experiment(result['experiment_id'])
        assert [t['user_message'] for t in detail['scenario']['turns']]==[t['user'] for t in snapshot['turns']]
        for _ in models: positions+=len(snapshot['turns'])
    assert positions==950

def test_history_uses_snapshot_and_only_current_model_prior_turns(private_bank):
    with private_bank() as db: models=[r['name'] for r in db.execute('SELECT name FROM ai_models WHERE active=1 ORDER BY name')][:2]
    eid=main.create_experiment(main.ExperimentRequest(scenario_code='DEP-01',model_names=models))['experiment_id']
    ids={}
    for model in models:
        for number in range(1,6):
            result=main.save_manual_response(main.ManualResponseRequest(experiment_id=eid,model_name=model,turn_number=number,response_text=f'{model}-response-{number}'))
            ids[model,number]=result['response_id']
    raw=main._get_response_context(ids[models[0],3])
    assert raw['user_message']==main.get_prompt('DEP-01')['turns'][2]['user']
    context=main._build_evaluation_context(raw)
    assert [t.turn_number for t in context.turns]==[1,2,3]
    assert [t.ai_response for t in context.turns]==[f'{models[0]}-response-{n}' for n in (1,2,3)]
    assert all(models[1] not in t.ai_response for t in context.turns)

def test_hash_tampering_fails_closed(tmp_path,monkeypatch):
    import shutil
    folder=tmp_path/'banks';shutil.copytree(prompt_loader.BANKS_DIR,folder)
    monkeypatch.setattr(prompt_loader,'BANKS_DIR',folder)
    target=folder/'MATRIZ-MAESTRA-20261016/DEP-01.json'
    target.write_text(target.read_text(encoding='utf8')+' ',encoding='utf8')
    with pytest.raises(ValueError,match='hash mismatch'):prompt_loader.load_prompt('DEP-01')

def test_existing_dep_experiment_keeps_prior_snapshot(private_bank):
    with private_bank() as db:
        row=db.execute("SELECT e.id, e.scenario_snapshot_json, s.id AS sid FROM experiments e JOIN scenarios s ON s.id=e.scenario_id WHERE s.code='DEP-01' AND e.scenario_snapshot_json IS NOT NULL ORDER BY e.id LIMIT 1").fetchone()
    if row is None: pytest.skip('No previous DEP-01 experiment')
    original=json.loads(row['scenario_snapshot_json'])
    assert main._read_experiment_snapshot(row['id'])==original
    detail=main.get_experiment(row['id'])
    assert [t['user_message'] for t in detail['scenario']['turns']]==[t['user'] for t in original['turns']]
    # A changed official bank does not silently upgrade historical experiments.
    with pytest.raises(ValueError,match='cambi'):
        main._require_experiment_snapshot_current(row['id'],'DEP-01',row['sid'])

def test_historical_without_snapshot_reads_legacy_rows(private_bank):
    with private_bank() as db:
        row=db.execute("SELECT e.id, e.scenario_id FROM experiments e JOIN scenarios s ON s.id=e.scenario_id WHERE s.code='DEP-01' ORDER BY e.id LIMIT 1").fetchone()
        assert row is not None
        # Remove only the private fixture snapshot to exercise the legacy read.
        db.execute('UPDATE experiments SET scenario_snapshot_json=NULL WHERE id=?',(row['id'],))
        expected=[{'id':r['turn_number'],'user':r['user_message']} for r in db.execute('SELECT turn_number,user_message FROM conversation_turns WHERE scenario_id=? ORDER BY turn_number',(row['scenario_id'],))]
    result=main._read_experiment_snapshot(row['id'])
    assert result['historical_read_only'] and result['turns']==expected
    assert result['turns'][2]['user']!=main.get_prompt('DEP-01')['turns'][2]['user']
