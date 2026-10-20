"""Build an immutable latest-evidence view; never overwrite previous runs."""
from pathlib import Path
import json
from .technical_critical_cases import cases
from .run_authorized_validation import save

def build(root, target, critical=False):
    root=Path(root); target=Path(target); target.mkdir(parents=True,exist_ok=False)
    latest={}
    folders=['critical_02'] if critical else ['live_01','recheck_01']
    for folder in folders:
        for file in (root/folder).glob('*.json'):
            packet=json.loads(file.read_text(encoding='utf-8'))
            if not isinstance(packet,dict) or 'decisions' not in packet:continue
            key=packet['case']['id']
            if key not in latest:latest[key]=packet
            else:latest[key]['decisions'].update(packet['decisions'])
            latest[key].setdefault('source_artifacts',[]).append(str(file))
    if critical:
        for case in cases():
            if case['id'] not in latest:
                latest[case['id']]={'case':case,'decisions':{code:{'code':code,'status':'PENDING','score':None,'reason':'Not yet read independently'} for code in case['codes']}}
    for key,packet in latest.items():save(target/(key+'.json'),packet)
    save(target/'manifest.json',{'sources':folders,'cases':len(latest),'policy':'Latest evidence per code, historical files preserved; pending is not a score.'})

if __name__=='__main__':
    import sys
    if len(sys.argv)>3 and sys.argv[3] in ('changed_contracts','causal','em_specific'):
        source=Path(sys.argv[1]);target=Path(sys.argv[2]);target.mkdir(parents=True,exist_ok=False)
        for file in source.glob('*.json'):
            packet=json.loads(file.read_text(encoding='utf-8'))
            packet['decisions']={code:d for code,d in packet['decisions'].items()
                if ((code.startswith(('AF','CE','CP','GD','PA')) or code=='PS6') if sys.argv[3]=='changed_contracts'
                    else code in (('EM9','IR8','PS3') if sys.argv[3]=='causal' else ('EM7','EM12')))}
            if packet['decisions']:save(target/file.name,packet)
    else:build(sys.argv[1],sys.argv[2],len(sys.argv)>3 and sys.argv[3]=='critical')
