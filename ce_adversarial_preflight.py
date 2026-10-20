"""CE2–CE10 preflight. Never invokes semantic runners or OpenAI."""
import argparse
import csv
import importlib
import inspect
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def prepare(cases_path):
    data = json.loads(Path(cases_path).read_text(encoding='utf-8'))
    cases = data['cases']
    if len(cases) != 29 or len({c['id'] for c in cases}) != len(cases):
        raise ValueError('Expected 29 unique adversarial cases')
    dispatcher = importlib.import_module('backend.evaluators.ce.pilot.integrate_ce2_ce10')
    if not {'indicator','user_text','response_text','history','semantic_runner','verifier_runner','verify_claim'}.issubset(inspect.signature(dispatcher.evaluate).parameters):
        raise ValueError('Dispatcher interface changed')
    bridges = {}
    for n in range(2, 11):
        name = f'CE{n}'
        letter = chr(96 + n)
        module = importlib.import_module(f'backend.evaluators.ce.ce_{letter}.ce{n}_provider_bridge')
        if n <= 8:
            for attr in (f'extract_ce{n}_draft',f'evaluate_ce{n}_with_verifier'):
                if not callable(getattr(module,attr,None)):
                    raise ValueError(f'{name} missing {attr}')
        else:
            for attr in ('extract','evaluate_with_verifier'):
                if not callable(getattr(module,attr,None)):
                    raise ValueError(f'{name} missing {attr}')
        bridges[name] = module.__name__
    records = []
    for c in cases:
        indicator = c['indicator']
        if indicator not in bridges:
            raise ValueError(f'Unexpected indicator: {indicator}')
        if not all(isinstance(c.get(k),str) and c[k].strip() for k in ('id','user_message','assistant_response')):
            raise ValueError(f'Missing original text in {c.get("id")}')
        raw = c.get('prior_history',[])
        history = None
        if indicator == 'CE10':
            history = []
            pending = None
            for m in raw:
                if not isinstance(m,dict) or m.get('role') not in ('user','assistant') or not isinstance(m.get('content'),str) or not m['content'].strip():
                    raise ValueError(f'Invalid CE10 message: {c["id"]}')
                if m['role']=='user':
                    if pending is not None: raise ValueError('Two consecutive user messages')
                    pending = m['content']
                else:
                    if pending is None: raise ValueError('Assistant message without user')
                    if m.get('model')=='Modelo_A':
                        history.append({'user':pending,'assistant':m['content']})
                    pending = None
            if pending is not None: raise ValueError('Unpaired user message')
        records.append({'id':c['id'],'indicator':indicator,'expected':c.get('expected'),
                        'status':'READY_OFFLINE_ONLY','user_message':c['user_message'],
                        'assistant_response':c['assistant_response'],'history':history,
                        'bridge':bridges[indicator], 'actual_score':None})
    return records


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases',default='casos_adversariales_ce2_ce10.json')
    p.add_argument('--out',default='resultados/prevuelo_ce2_ce10')
    args=p.parse_args(argv)
    records=prepare(args.cases)
    dest=Path(args.out)
    dest.mkdir(parents=True,exist_ok=True)
    payload={'mode':'OFFLINE_NO_API','semantic_validation_performed':False,
             'created_at_utc':datetime.now(timezone.utc).isoformat(),
             'cases':records,'counts':dict(Counter(r['indicator'] for r in records))}
    (dest/'prevuelo.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    with (dest/'prevuelo.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=['id','indicator','expected','status','bridge','actual_score'])
        writer.writeheader()
        writer.writerows({k:r[k] for k in writer.fieldnames} for r in records)
    print(f'PREVUELO CORRECTO: {len(records)} casos, CE2–CE10. SIN llamadas OpenAI.')
    print(f'Archivos: {dest / "prevuelo.json"} | {dest / "prevuelo.csv"}')


if __name__=='__main__':
    main()
