"""Candidate reader integration over immutable, verified version2 scoring.

No provider, credentials, cache, expected score or implicit network access.
"""
from pathlib import Path
from hashlib import sha256
import json
from backend.evaluators.ansiedad_semantic.engine import evaluate_turn as frozen_evaluate
from backend.evaluators.ansiedad_semantic import component_routes,em_component_adapter
from .reader_contract import candidate_request

VERSION='ANXIETY-CANDIDATE-20261013-3'
FROZEN=Path('docs/ansiedad_semantic/closure6_20261013/integral_live/ratification_06')

def verify_frozen():
    freeze=json.loads((FROZEN/'FREEZE.json').read_text(encoding='utf-8'))
    assert freeze['release_id']=='ANXIETY-TECHNICAL-20261013-2'
    assert sha256((FROZEN/'code_manifest.json').read_bytes()).hexdigest()==freeze['code_manifest_sha256']
    for name in ['code_manifest.json','files.json']:
        for row in json.loads((FROZEN/name).read_text(encoding='utf-8')):
            if sha256(Path(row['path']).read_bytes()).hexdigest()!=row['sha256']:
                raise ValueError('Frozen dependency changed: '+row['path'])

def evaluate_turn(originals,conversation,model,turn,*,reader,resource_checks=()):
    verify_frozen()
    def candidate_reader(request):
        return reader(candidate_request(request))
    result=frozen_evaluate(originals,conversation,model,turn,reader=candidate_reader,resource_checks=resource_checks)
    result['engine_version']=VERSION
    for row in result['rows']:row['engine_version']=VERSION
    return result

def adjudicate(code,context,a,b):
    # Contract clarifications affect readers, never rewrite old component facts.
    return em_component_adapter.adjudicate(code,context,a,b) if code.startswith('EM') else component_routes.adjudicate(code,context,a,b)
