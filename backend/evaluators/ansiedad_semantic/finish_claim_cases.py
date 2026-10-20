"""Select previously read factual claims for a new independent audit, without new gold labels."""
import json
from pathlib import Path
from .run_authorized_validation import save

def build(target):
    root=Path('docs/ansiedad_semantic/finish_20261013')
    corpus=json.loads((root/'coverage_preregistered.json').read_text(encoding='utf-8'))
    selected={'coverage-CP1-1','coverage-IR2-1','coverage-PA1-1','coverage-EM1-1','coverage-ND6-2'}
    rows=[{**case,'id':'claim-audit-'+case['id'],'qualification':
        'A new claim-verification protocol on development data; extraction may be reused by exact request hash. No target note supplied.'}
        for case in corpus if case['id'] in selected]
    for name in ('GD-omission__GD7','PS-omission__PS6'):
        packet=json.loads((root/'step1_pairs_01'/(name+'.json')).read_text(encoding='utf-8'))
        rows.append({**packet['case'],'id':'claim-audit-'+name,'qualification':
            'Audit composite limits protection; no automatic resolution of a rejected extraction.'})
    save(Path(target),rows)

if __name__=='__main__':
    import sys
    build(sys.argv[1])
