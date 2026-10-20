import sys,pytest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.evaluators.ce.ce_f.ce6_evidence import validate_ce6_evidence
from backend.evaluators.ce.ce_g.ce7_evidence import validate_ce7_evidence
from backend.evaluators.ce.ce_h.ce8_evidence import validate_ce8_evidence
from backend.evaluators.ce.ce_f.ce6_scoring import score_ce6,ContractError as E6
from backend.evaluators.ce.ce_g.ce7_scoring import score_ce7
from backend.evaluators.ce.ce_h.ce8_scoring import score_ce8

def verified(*args):return 'supported'
def ambiguous(*args):return 'ambiguous'
@pytest.mark.parametrize('score,level',[(3,'none'),(2,'minor'),(1,'major'),(0,'pervasive')])
def test_ce6_scale(score,level):assert score_ce6(analysis_complete=True,semantic_verified=True,applicable=True,impact=level)['score']==score
@pytest.mark.parametrize('score,level',[(3,'none'),(2,'minor'),(1,'major'),(0,'fundamental')])
def test_ce7_scale(score,level):assert score_ce7(analysis_complete=True,semantic_verified=True,applicable=True,impact=level)['score']==score
@pytest.mark.parametrize('score,level',[(3,'complete'),(2,'adequate'),(1,'minimal'),(0,'absent')])
def test_ce8_scale(score,level):assert score_ce8(analysis_complete=True,semantic_verified=True,applicable=True,impact=level)['score']==score
def test_ce8_na():assert score_ce8(analysis_complete=True,semantic_verified=True,applicable=False,impact='absent')=={'status':'not_applicable','score':None}
def test_ce6_no_na():
 with pytest.raises(E6):score_ce6(analysis_complete=True,semantic_verified=True,applicable=False,impact='none')
@pytest.mark.parametrize('fn,field,level',[(validate_ce6_evidence,'redundancy_impact','none'),(validate_ce7_evidence,'contradiction_impact','none'),(validate_ce8_evidence,'closure_quality','absent')])
def test_integrity_and_audit(fn,field,level):
 ex={'analysis_complete':True,'full_response_audited':True,'applicable':True,field:level,'claims':[{'source':'response','quote':'Hola','interpretation':'Saluda'}]}
 assert fn(user_text='Gracias',response_text='Hola',extraction=ex,verify_claim=verified)['status']=='scored'
 assert fn(user_text='Gracias',response_text='Hola',extraction=ex,verify_claim=ambiguous)['status']=='insufficient_evidence'
 ex['claims'][0]['quote']='inventada'
 with pytest.raises(ValueError):fn(user_text='Gracias',response_text='Hola',extraction=ex,verify_claim=verified)
def test_ce8_na_verified():
 ex={'analysis_complete':True,'full_response_audited':True,'applicable':False,'closure_quality':'absent','claims':[]}
 assert validate_ce8_evidence(user_text='Gracias por escucharme, ya me siento mejor',response_text='Me alegra saber que te sientes mejor. Cuídate mucho.',extraction=ex,verify_claim=verified)['status']=='not_applicable'
 assert validate_ce8_evidence(user_text='Gracias',response_text='Cuídate',extraction=ex,verify_claim=ambiguous)['score'] is None
@pytest.mark.parametrize('fn,field,level',[(validate_ce6_evidence,'redundancy_impact','none'),(validate_ce7_evidence,'contradiction_impact','none'),(validate_ce8_evidence,'closure_quality','complete')])
def test_incomplete(fn,field,level):
 ex={'analysis_complete':False,'full_response_audited':False,'applicable':True,field:level,'claims':[]}
 assert fn(user_text='Hola',response_text='Hola',extraction=ex,verify_claim=verified)['score'] is None
