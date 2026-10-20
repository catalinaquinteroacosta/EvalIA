from backend.evaluators.ansiedad_semantic.engine import evaluate_turn
from backend.evaluators.ansiedad_semantic.identified_context import OriginalTurn

def test_all_81_provider_failures_remain_blocked_without_complete_percent():
    def unavailable(_):raise OSError('No API authorized')
    result=evaluate_turn([OriginalTurn('c','m',1,'Estoy triste.','Te escucho.')],'c','m',1,reader=unavailable)
    assert len(result['rows'])==81
    assert len(result['families'])==9
    ce10=next(r for r in result['rows'] if r['code']=='CE10')
    assert ce10['status']=='N/A'
    assert ce10['verified_gate_basis']['prior_history']==[]
    assert result['summary']['counts']['BLOCKED']==80
    assert result['summary']['percentage'] is None
    assert result['summary']['scored_denominator']==0
    assert not result['summary']['complete']

def test_no_future_or_other_model_in_any_of_eighteen_blind_requests():
    rows=[OriginalTurn('c','m',1,'pasado propio','respuesta propia'),OriginalTurn('c','m',2,'actual','respuesta actual'),
          OriginalTurn('c','m',3,'FUTURO','FUTURO'),OriginalTurn('c','otro',1,'AJENO','AJENO')]
    requests=[]
    def reader(request):
        requests.append(request)
        raise OSError('offline')
    result=evaluate_turn(rows,'c','m',2,reader=reader)
    assert len(requests)==9  # failed extraction suppresses unnecessary verification
    assert all(request['original']['prior_history']==[{'role':'user','text':'pasado propio'},{'role':'assistant','text':'respuesta propia'}] for request in requests)
    assert result['original']['response']=='respuesta actual'
