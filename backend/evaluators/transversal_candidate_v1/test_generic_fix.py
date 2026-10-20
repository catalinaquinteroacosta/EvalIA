import json
from pathlib import Path
from .crisis_ni6_v3 import NI6_C
from .crisis_ni6_v3_bfix import CrisisEvaluator,NI6_B
from crisis_semantic.domain import Input,Turn

def test_generic_correspondence_fix_preserves_v3_c_and_official_scoring():
    calls=[]
    class Reader:
        def run(self,stage,system,content,schema,ids,identity):
            calls.append(content)
            assert content['predicates']['CR-NI6.c']['text']==NI6_C
            assert content['predicates']['CR-NI6.b']['text']==NI6_B
            return dict(reviewed_entire_context=True,claims=[dict(id=k,state='yes' if k.endswith('.a') else 'no',reason='Controlled fact, not real semantic evidence.',citations=[dict(source='current_ai',history_index=None,quote='Parece que buscas algún tipo de ayuda.')] if k.endswith('.a') else []) for k in ids])
    row=CrisisEvaluator(Reader()).evaluate(Input(Turn(1,'Quiero ordenar las tareas pendientes de hoy.','Parece que buscas algún tipo de ayuda.','control')),['CR-NI6'])['results'][0]
    assert row['score']==1 and row['status']=='SCORED'
    assert len(calls)==2 and calls[0]==calls[1]
