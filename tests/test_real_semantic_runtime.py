import json
from pathlib import Path
from unittest.mock import patch
import pytest
from backend.real_semantic_runtime import Budget,configure,MODEL

def config(tmp):
 return dict(explicit_user_approval=True,authorization_id='test',model=MODEL,max_usd='1',max_calls=1,journal_directory=str(tmp/'journal'),allowed_experiment_ids=[1])

def test_no_approval_no_reader(tmp_path):
 p=tmp_path/'authorization.json';p.write_text(json.dumps({**config(tmp_path),'explicit_user_approval':False}))
 with pytest.raises(ValueError):configure(None,p)

def test_budget_reservation_failure_not_retried(tmp_path,monkeypatch):
 monkeypatch.setenv('OPENAI_API_KEY','test-secret-never-sent')
 budget=Budget(config(tmp_path))
 body=dict(model=MODEL,max_output_tokens=10,input=[])
 try:
  with patch('backend.real_semantic_runtime.urlopen',side_effect=OSError('offline')) as transport:
   with pytest.raises(RuntimeError):budget.request(body,'responses')
   with pytest.raises(RuntimeError):budget.request(body,'responses')
   with pytest.raises(RuntimeError):budget.request({**body,'input':['different']},'responses')
   assert transport.call_count==1
   assert 'test-secret' not in budget.path.read_text()
 finally:budget.close()

def test_process_and_authorization_restart_guard(tmp_path):
 c=config(tmp_path);budget=Budget(c)
 with pytest.raises(FileExistsError):Budget(c)
 budget.close()
 with pytest.raises(ValueError):Budget({**c,'max_usd':'2'})

def test_configuration_exact_qualified_provider(tmp_path,monkeypatch):
 from types import SimpleNamespace
 monkeypatch.setenv('OPENAI_API_KEY','test-secret-never-sent')
 p=tmp_path/'authorization.json';p.write_text(json.dumps(config(tmp_path)))
 app=SimpleNamespace(state=SimpleNamespace())
 with patch('backend.real_semantic_runtime.urlopen',side_effect=AssertionError('No network')):
  budget=configure(app,p)
 try:
  deps=app.state.evaluation_dependencies
  assert deps['crisis_provider'].model==MODEL
  assert {'CR-RI2','CR-CE10'}<=deps['crisis_provider'].qualified_components
  assert deps['allowed_experiment_ids']==[1]
  assert not budget.path.exists()
 finally:budget.close()

def test_settled_request_reuse_and_evidence_integrity(tmp_path,monkeypatch):
 from io import BytesIO
 monkeypatch.setenv('OPENAI_API_KEY','test-secret-never-sent')
 budget=Budget(config(tmp_path));body=dict(model=MODEL,max_output_tokens=10,input=[])
 raw=dict(model=MODEL,usage=dict(input_tokens=10,output_tokens=1,input_tokens_details={'cached_tokens':4}))
 try:
  with patch('backend.real_semantic_runtime.urlopen',return_value=BytesIO(json.dumps(raw).encode())) as transport:
   assert budget.request(body,'responses')==raw
   assert budget.request(body,'responses')==raw
   assert transport.call_count==1
  settled=budget.events()[-1]
  assert settled['actual_usd']=='0.000022'
  (budget.root/settled['artifact']).write_text('{}')
  with pytest.raises(RuntimeError):budget.request(body,'responses')
 finally:budget.close()
