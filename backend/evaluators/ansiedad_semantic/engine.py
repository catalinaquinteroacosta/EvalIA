"""Anxiety-only research engine. No implicit API, cache or shared runner.

OriginalTurn identities are the sole history authority. Readers are explicit
injected capabilities; offline tests provide stubs, live work requires a
separately authorized budgeted reader. Scores always come from Python.
"""
from .identified_context import authorized_context
from .official_contracts import EXPECTED
from . import component_routes, em_component_adapter
from .result_tables import aggregate

VERSION='ANXIETY-INTEGRAL-20261012-1'

def evaluate_turn(originals,conversation,model,turn,*,reader,resource_checks=()):
    identified=authorized_context(originals,conversation,model,turn)
    rows=[]; artifacts={}
    for family,count in EXPECTED.items():
        try:
            artifacts[family]=(em_component_adapter.run_family(identified,reader=reader) if family=='EM'
                else component_routes.run_family(identified,family,reader=reader,resource_checks=resource_checks))
        except Exception as error:
            artifacts[family]={'results':{f'{family}{i}':{'code':f'{family}{i}','status':'BLOCKED','score':None,
                'reason':f'{type(error).__name__}: {error}'} for i in range(1,count+1)}}
        for i in range(1,count+1):
            code=f'{family}{i}'
            decision=artifacts[family]['results'][code]
            status=decision['status']
            rows.append({**decision,'conversation':conversation,'model':model,'turn':turn,'family':family,
                'input_sha256':identified['input_sha256'],'engine_version':VERSION,
                'applicability':'APPLICABLE' if status=='SCORED' else 'NOT_APPLICABLE' if status=='N/A' else 'UNRESOLVED',
                'gate_reason':decision['reason'] if status=='N/A' else ''})
    return {'original':identified,'rows':rows,'families':artifacts,'summary':aggregate(rows,expected_count=81),
            'clinical_validation':False,'engine_version':VERSION}
