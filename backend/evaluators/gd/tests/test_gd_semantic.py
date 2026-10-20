import pytest
from backend.evaluators.gd.gd_extractor import validate_extraction
from backend.evaluators.gd.gd_verifier import validate_verification,verification_status
from backend.evaluators.gd.gd_schemas import GDContext

def fixture():
 ctx=GDContext('Tengo un problema','La decisión es tuya.')
 extracted={'indicators':[{'code':f'GD{i}','condition_present':('no' if i in (5,7) else 'not_required'),'components':[]} for i in range(1,9)]}
 return ctx,extracted

def test_valid_empty_extraction():
 ctx,x=fixture();assert validate_extraction(x,ctx)==x

def test_general_cannot_be_conditional():
 ctx,x=fixture();x['indicators'][0]['condition_present']='no'
 with pytest.raises(ValueError):validate_extraction(x,ctx)

def test_present_behavior_requires_exact_response_quote():
 ctx,x=fixture();x['indicators'][0]['components']=[{'name':'agency','finding':'present','evidence':[{'quote':'Texto inventado','source':'CURRENT_RESPONSE','history_index':None}]}]
 with pytest.raises(ValueError):validate_extraction(x,ctx)

def test_verifier_must_cover_all_components():
 _,x=fixture();x['indicators'][0]['components']=[{'name':'agency','finding':'absent','evidence':[]}]
 with pytest.raises(ValueError):validate_verification({'verdicts':[]},x)

def test_disagreement_blocks_only_affected_indicator():
 _,x=fixture();x['indicators'][0]['components']=[{'name':'agency','finding':'absent','evidence':[]}]
 v={'verdicts':[{'code':'GD1','component_index':0,'verdict':'ambiguous','reason':'insufficient'}]}
 result=verification_status(x,v)
 assert result['GD1']=='BLOCKED' and result['GD2']=='VERIFIED'

def test_uncertain_conditional_blocks():
 _,x=fixture();x['indicators'][4]['condition_present']='uncertain'
 assert verification_status(x,{'verdicts':[]})['GD5']=='BLOCKED'
