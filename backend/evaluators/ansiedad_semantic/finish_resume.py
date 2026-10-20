"""Resume preregistered cases that have no completed pair, never repeat accepted files."""
from pathlib import Path
import json
from .run_authorized_validation import save

def run(source,completed,target):
    corpus=json.loads(Path(source).read_text(encoding='utf-8'))
    done=set()
    for folder in completed:
        for file in Path(folder).glob('*.json'):
            packet=json.loads(file.read_text(encoding='utf-8'))
            if isinstance(packet,dict) and 'case' in packet and 'decisions' in packet:
                done.add(packet['case']['id'])
    save(Path(target),[case for case in corpus if case['id'] not in done])

if __name__=='__main__':
    import sys
    run(sys.argv[1],sys.argv[2:-1],sys.argv[-1])
