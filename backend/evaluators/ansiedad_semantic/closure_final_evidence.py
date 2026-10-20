"""Reproduce the entire private engine using only preserved real role outputs."""
import copy,json,sys
from pathlib import Path
from hashlib import sha256
from .closure_integral_live import LIVE,read,save
from .engine import evaluate_turn
from .identified_context import OriginalTurn
from .scoped_072_audit import get_scope,paired
from .result_tables import export_new

def integration():
    base=Path('docs/ansiedad_semantic/finish_20261013/step3_engine_01')
    maps={'extract':{},'independent_verify':{}};trace={};original=None
    def put(stage,reading,path,codes):
        for c in codes:
            maps[stage][c]=copy.deepcopy(reading['indicators'][c])
            trace.setdefault(c,{})[stage]={'path':str(path),'sha256':sha256(path.read_bytes()).hexdigest()}
    for path in sorted(base.glob('call_??.json')):
        d=read(path)
        if 'request' not in d:continue
        q=d['request']
        if original is None:original=q['original']
        assert q['original']==original
        put(q['stage'],d['reading'],path,q['indicators'])
    for family in ['AF','ND','CP','IR','EM']:
        p=LIVE/('integration-affected-'+family+'_01')
        for stage in maps:
            path=p/(stage+'.json');d=read(path)
            assert d['request']['original']==original
            put(stage,d['reading'],path,d['request']['indicators'])
    for name,codes in [('AF-gates',['AF2','AF3']),('integration-IR3-conclusion',['IR3']),('integration-EM1-congruence-verify',['EM1'])]:
        p=LIVE/('component_revision_'+name+'_01')
        for stage,file in [('extract','merged_extraction.json'),('independent_verify','merged_verification.json')]:
            path=p/file;d=read(path);assert d['original']==original
            put(stage,d['reading'],path,codes)
    for name in ['CEverify_CE1_CE2_01','CEverify_CE3_01','CEverify_CE4_CE5_CE6_CE7_CE8_CE9_CE10_01']:
        path=LIVE/name/'independent_verify.json';d=read(path);assert d['request']['original']==original
        put('independent_verify',d['reading'],path,d['request']['indicators'])
    return original,maps,trace

def experiment():
    o,rows=get_scope();maps={'extract':{},'independent_verify':{}};trace={}
    for row in rows:
        c=row['code']
        if c=='CE10':continue # official first-turn gate in canonical engine
        if c in ('IR6','EM9'):
            p=LIVE/('component_revision_072-IR6-literal_01' if c=='IR6' else 'component_revision_072-EM9-gates_01')
            for stage,file in [('extract','merged_extraction.json'),('independent_verify','merged_verification.json')]:
                path=p/file;d=read(path);assert d['original']==o
                maps[stage][c]=d['reading']['indicators'][c]
                trace.setdefault(c,{})[stage]={'path':str(path),'sha256':sha256(path.read_bytes()).hexdigest()}
        else:
            a,b,path=paired(row);maps['extract'][c]=a;maps['independent_verify'][c]=b
            trace[c]={'paired_source':str(path),'sha256':sha256(path.read_bytes()).hexdigest(),
                'private_artifacts':row.get('paired_private_artifacts',[])}
    return o,maps,trace

def replay(o,maps):
    originals=[]
    for index in range(0,len(o['prior_history']),2):
        u,a=o['prior_history'][index:index+2]
        assert u['role']=='user' and a['role']=='assistant'
        originals.append(OriginalTurn(o['conversation'],o['model'],index//2+1,u['text'],a['text']))
    originals.append(OriginalTurn(o['conversation'],o['model'],o['turn'],o['user'],o['response']))
    calls=[]
    def reader(q):
        assert q['original']==o, 'Original/history identity changed during engine replay'
        stage=q['stage'];codes=list(q['indicators'])
        calls.append({'stage':stage,'codes':codes,'network':False})
        return {'indicators':{c:copy.deepcopy(maps[stage][c]) for c in codes}}
    result=evaluate_turn(originals,o['conversation'],o['model'],o['turn'],reader=reader)
    assert result['original']==o
    return result,calls

def run(version):
    out=LIVE/('final_engine_replay_'+version);out.mkdir(exist_ok=False)
    summaries={}
    for name,load in [('integration',integration),('experiment072_ChatGPT_1',experiment)]:
        o,maps,trace=load();result,calls=replay(o,maps)
        p=out/name;p.mkdir()
        save(p/'engine_result.json',result);save(p/'real_evidence_sources.json',trace)
        save(p/'replay_calls.json',{'calls':calls,'new_paid_requests':0,'real_component_readings_reused':True,
            'not_a_new_blind_holdout':'These are known integration/regression and the existing 072 anchor, not an untouched holdout.'})
        export_new(p/'tables',result['rows']);summaries[name]=result['summary']
    save(out/'summary.json',summaries)
    print(json.dumps(summaries))

if __name__=='__main__':run(sys.argv[1] if len(sys.argv)>1 else '01')
