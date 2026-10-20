import copy
import pytest
from backend.evaluators.ansiedad_semantic.claim_verifier import ClaimAuditReader,verification_request

def request(stage='independent_verify'):
    return {'stage':stage,'original':{'input_sha256':'one','user':'Original user','response':'Original response'},
        'indicators':{'PA3':{'components':{'execution': 'Explain use'}}}}

def test_proposal_is_untrusted_and_originals_not_mutated():
    original=request();before=copy.deepcopy(original);proposal={'indicators':{'PA3':{'components':{}}}}
    q=verification_request(original,proposal)
    assert original==before and q['original']==original['original']
    assert q['untrusted_proposed_components']==proposal
    assert not ({'expected','score','basis','split'} & q.keys())
    q['untrusted_proposed_components'].clear()
    assert proposal

def test_verifier_can_reject_proposal_without_overwriting_extraction():
    calls=[]
    def provider(q):
        calls.append(q)
        return {'indicators':{'PA3':{'components':{'execution':q['stage']=='extract'}}}}
    reader=ClaimAuditReader(provider)
    a=reader(request('extract'));b=reader(request())
    assert a!=b and calls[1]['untrusted_proposed_components']==a

def test_other_originals_cannot_borrow_proposal():
    reader=ClaimAuditReader(lambda q:{})
    reader(request('extract'));q=request();q['original']['input_sha256']='other'
    with pytest.raises(ValueError,match='exact originals'):reader(q)
