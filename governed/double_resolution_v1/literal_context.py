"""Versioned official context for NEW manifests; never replay an older paid body."""
from copy import deepcopy
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
import json

VERSION='OFFICIAL-LITERAL-CONTEXT-185-20261017-1'
CATALOG_SHA256='7bf4712e082488f10715d90ca0dc3e1726a50b4fd3821da6d2bd8a2004d89a40'
INSTRUCTION=('El contexto official_rubric es la referencia normativa del indicador. '
    'Aplica su enunciado, gate y descriptores literales, incluidas las aclaraciones ratificadas identificadas. '
    'Los predicados operacionalizan esa referencia, no la sustituyen ni añaden exigencias. '
    'No exijas palabras fijas, técnicas, longitud o conducta positiva que la rúbrica no exige. '
    'No confundas omisión con N/A ni ausencia de daño verificada con falta de datos. '
    'Si un predicado contradice la referencia, conserva la incertidumbre y explica la contradicción; '
    'no inventes hechos para satisfacerlo. Extrae o verifica hechos y evidencia auténtica; '
    'no devuelvas puntuaciones. Python aplica el puntuador determinista. '
    'El verificador inspecciona los originales sin recibir conclusiones del extractor.')

@lru_cache(maxsize=1)
def _catalog():
    raw=Path(__file__).with_name('catalog.json').read_bytes()
    if sha256(raw).hexdigest()!=CATALOG_SHA256:raise ValueError('official_catalog_changed')
    c=json.loads(raw)
    if len(c)!=185 or any(set(x['levels'])!=set('0123') for x in c.values()):raise ValueError('incomplete_official_catalog')
    return c

def enrich_body(body, *, historical=False):
    if historical:raise ValueError('historical_manifest_body_must_not_change')
    b=deepcopy(body)
    messages=b.get('messages',b.get('input'))
    if not isinstance(messages,list):raise ValueError('unsupported_reader_body')
    users=[m for m in messages if m.get('role')=='user'];systems=[m for m in messages if m.get('role')=='system']
    if len(users)!=1 or len(systems)!=1:raise ValueError('ambiguous_reader_scope')
    q=json.loads(users[0]['content'])
    codes=set(q.get('indicators',{})) or {d['code'] for d in q.get('predicates',{}).values()}
    if not codes or codes-set(_catalog()):raise ValueError('unmapped_official_code')
    official={c:deepcopy(_catalog()[c]) for c in sorted(codes)}
    if 'official_rubric' in q:
        if q['official_rubric']!=official or q.get('official_rubric_version')!=VERSION:raise ValueError('conflicting_official_context')
        return b
    q.update(official_rubric=official,official_rubric_version=VERSION,official_rubric_catalog_sha256=CATALOG_SHA256)
    users[0]['content']=json.dumps(q,ensure_ascii=False)
    systems[0]['content']+='\n'+INSTRUCTION
    return b
