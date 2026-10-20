"""REJECTED / NOT FIT FOR PRODUCTION — historical experimental variant only.

Keep isolated requests identical; remove only their discarded family observations.
Remote semantic equivalence requires qualification before activation.
"""
from copy import deepcopy
from backend import luna_reader as reader

VERSION = 'ANXIETY-DISJOINT-SCOPES-CANDIDATE-1'
PRODUCTION_APPROVED = False
STATUS = 'REJECTED_DISABLED'

def family_request(request):
    reduced=deepcopy(request)
    reduced['indicators']={code:row for code,row in reduced['indicators'].items()
                           if code not in reader.ISOLATED_ANXIETY_CODES}
    reduced.pop('literal_citation_catalog',None)
    reduced.pop('citation_instruction',None)
    return reduced

def read_anxiety(request,transport):
    from backend.evaluators.ansiedad_semantic.budgeted_reader import envelope
    from backend.luna_application import BatchPending
    pending=False
    reading={'indicators':{}}
    scopes=[]
    family=family_request(request)
    if family['indicators']:scopes.append(family)
    scopes.extend(reader.isolated_anxiety_request(request,code)
                  for code in sorted(reader.ISOLATED_ANXIETY_CODES.intersection(request['indicators'])))
    for scope in scopes:
        try:
            own=reader.decode_anxiety(transport(reader.adapt_body(envelope(scope,reader.MODEL),
                'ansiedad_depresion',scope['stage']),'chat/completions'),scope)
            reading['indicators'].update(own['indicators'])
        except BatchPending:pending=True
    return {'indicators':{}} if pending else reading
