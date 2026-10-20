from backend.evaluators.ps.preflight import audit

def test_all_indicators_have_full_rubric():
    result=audit()
    assert result['indicators']==[f'PS{i}' for i in range(1,11)]
    assert result['error_count']==0

def test_preflight_is_offline_and_reports_validation_limitations():
    result=audit()
    assert result['api_calls']==0
    assert result['review_count']>=3
