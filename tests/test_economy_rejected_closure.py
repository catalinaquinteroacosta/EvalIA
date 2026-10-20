"""Focal offline closure of rejected economy variant; never calls a provider."""
import ast,json
from pathlib import Path
from hashlib import sha256
from collections import defaultdict
from urllib.request import urlopen
from backend import luna_reader as reader,luna_anxiety_economy as rejected
ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'.evalia-private/luna_ui/plans/f2ca66042f384c6289cb485168c284cd'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def test_production_routes_only_original():
    assert rejected.PRODUCTION_APPROVED is False and rejected.STATUS=='REJECTED_DISABLED'
    for name in ('luna_real_ui.py','luna_runner.py','validation_runtime.py','luna_sync_runtime.py','main.py','integrated_evaluation.py'):
        tree=ast.parse((ROOT/'backend'/name).read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):assert all('luna_anxiety_economy' not in x.name for x in node.names)
            if isinstance(node,ast.ImportFrom):
                assert 'luna_anxiety_economy' not in (node.module or '')
                assert all('luna_anxiety_economy' not in x.name for x in node.names)
    js=(ROOT/'frontend/real_mode.js').read_text(encoding='utf-8-sig')
    assert "'/api/real/prepare'" in js and 'luna_anxiety_economy' not in js
    prod=(ROOT/'backend/luna_real_ui.py').read_text(encoding='utf-8')
    assert 'reader.read_anxiety(request,capture)' in prod and 'reader.read_anxiety(request,call)' in prod

def test_original_plan_coverage_blind_scopes_and_identity():
    manifest=read(FOLDER/'manifest.json');assert len(manifest['requests'])==850
    assert manifest['reader_sha256']==sha256(Path(reader.__file__).read_bytes()).hexdigest()
    for name,digest in manifest['runtime_sources'].items():assert sha256((ROOT/'backend'/(name+'.py')).read_bytes()).hexdigest()==digest
    groups=defaultdict(list);codes=set()
    for row in manifest['requests']:
        p=json.loads(row['body']['messages'][1]['content']);o=p['original'];groups[(o['model'],o['turn'])].append(p);codes.update(p['indicators'])
    assert len(codes)==81 and len(groups)==25
    for rows in groups.values():
        assert len(rows)==34
        for code in reader.ISOLATED_ANXIETY_CODES:
            scopes=[p for p in rows if set(p['indicators'])=={code}]
            assert {p['stage'] for p in scopes}=={'extract','independent_verify'} and len(scopes)==2
            assert scopes[0]['original']==scopes[1]['original']
    assert len(reader.ISOLATED_ANXIETY_CODES)==8

def test_108_responses_match_original_sealed_plan_and_no_execution():
    with urlopen('http://127.0.0.1:8879/api/experiments/108/results') as f:current=json.load(f)
    rows=current['results'];assert len(rows)==25 and not any(r['evaluated'] for r in rows)
    saved={(r['model']['name'],r['turn_number']):r for r in rows};assert len(saved)==25
    for request in read(FOLDER/'manifest.json')['requests']:
        o=json.loads(request['body']['messages'][1]['content'])['original'];s=saved[o['model'],o['turn']]
        assert o['user']==s['user_message'] and o['response']==s['response_text']
        history=[]
        for t in range(1,o['turn']):
            previous=saved[o['model'],t];history.extend([{'role':'user','text':previous['user_message']},{'role':'assistant','text':previous['response_text']}])
        assert o['prior_history']==history
    state=read(FOLDER/'state.json');assert state['status']=='prepared' and not state['confirmed']
    assert state['estimated_reserve_usd']=='42.21702150'
    assert not (FOLDER/'authorization.json').exists()
    assert not list(FOLDER.rglob('*.intent.json')) and not list(FOLDER.rglob('*.receipt.json'))
