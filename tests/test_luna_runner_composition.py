"""Offline inventory/scope composition test, not semantic inference."""
from backend.luna_runner import IntegrationRunner


def test_special_qualification_routes_disjoint_and_full_inventory(monkeypatch):
    calls=[]
    class Evaluator:
        def __init__(self,*args,**kwargs):pass
        def evaluate(self,context,codes):
            calls.append((context,list(codes)))
            return dict(results=[dict(code=c,status='BLOCKED',score=None,applicable=True) for c in codes])
    monkeypatch.setattr('backend.luna_reader.LunaCrisisEvaluator',Evaluator)
    originals=[dict(conversation='999:LIBRE',model='offline',turn=i,user='question '+str(i),response='answer '+str(i)) for i in range(1,4)]
    record=dict(rubric_type='crisis',model='offline',turn=2,conversation='999:LIBRE',originals=originals)
    selected=IntegrationRunner(lambda _:record,crisis_provider=object()).evaluate_response(1)
    assert len(selected['indicator_results'])==104
    assert len({r['code'] for r in selected['indicator_results']})==104
    assert calls[1][1]==['CR-RI2'] and calls[2][1]==['CR-CE10']
    assert not {'CR-RI2','CR-CE10'}&set(calls[0][1])
    assert all(ctx.current.number==2 and [t.number for t in ctx.history]==[1] for ctx,_ in calls)
    assert selected['aggregation']['global_v2'] is None
