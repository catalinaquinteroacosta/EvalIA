import sys,json,hashlib,importlib.util,types
from pathlib import Path
from collections import Counter,defaultdict
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),str(ROOT/'backend/evaluators'),str(ROOT/'venv/Lib/site-packages')]
from backend.evaluators.ansiedad_semantic import component_routes,em_component_adapter,guardrail_review,af_component_adapter
from backend.evaluators.nd.contracts import TurnContext,HistoryTurn
def read(p):return json.loads(p.read_text(encoding='utf8'))
def load(name):
    spec=importlib.util.spec_from_file_location('bulk_'+name,HERE/'candidate'/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
F=load('functional_review');G=load('gd_component_review');P=load('paired_reading');N=load('nd_score');NP=load('nd_protocol');NP.score=N.score
REG=read(HERE/'COVERAGE_REGISTRY.json')
def clone(fn,extra):
    namespace={**fn.__globals__,**extra};return types.FunctionType(fn.__code__,namespace,fn.__name__,fn.__defaults__,fn.__closure__)
def candidate(code,ctx,a,b):
    if code.startswith('ND') and code!='ND1':
        r=NP.adjudicate(code,{'current':ctx},{'cases':{'current':a}},{'cases':{'current':b}})['current']
        return dict(status='N/A' if r.status=='NA' else r.status,score=r.score,reason=r.reason)
    route=component_routes.route(code) if not code.startswith('EM') else em_component_adapter
    if route.__name__.endswith('functional_review'):return F.adjudicate(code,ctx,a,b)
    if route.__name__.endswith('gd_component_review'):return G.adjudicate(code,ctx,a,b)
    if route in (guardrail_review,af_component_adapter):
        def resolve(*args,**kwargs):return P.resolve(*args,**kwargs,coverage_components=frozenset(REG.get(code,())))
        return clone(route.adjudicate,{'resolve':resolve})(code,ctx,a,b)
    return component_routes.adjudicate(code,ctx,a,b) if not code.startswith('EM') else em_component_adapter.adjudicate(code,ctx,a,b)
