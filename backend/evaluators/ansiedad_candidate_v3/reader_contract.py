"""Isolated combined reader candidate; no frozen scorer or evidence mutation."""
from copy import deepcopy
from . import em_contract as em, nd_contract as nd

def candidate_request(request):
    q=deepcopy(request)
    if 'EM5' in q['indicators']:
        fragment=em.candidate_request({'indicators':{'EM5':q['indicators']['EM5']}})
        q['indicators']['EM5']=fragment['indicators']['EM5']
    return nd.candidate_request(q)
