"""Bind an execution approval to the exact installed code and official scorers."""
import json,hashlib
from pathlib import Path
def verify(approval):
    here=Path(__file__).resolve().parent;root=here.parents[1];raw=(here/'RELEASE.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=approval.get('release_sha256'):raise ValueError('approval for different release')
    data=json.loads(raw)
    for name,h in data['files'].items():
        if hashlib.sha256((here/name).read_bytes()).hexdigest()!=h:raise ValueError('adjudication code changed')
    for name,h in data['official_dependencies'].items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=h:raise ValueError('official scorer dependency changed')
    return True
