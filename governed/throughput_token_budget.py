"""Offline proxy tokenization with margins; never alters request bodies or output caps."""
import os,sys,json,math,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]/'isolated_concurrency_step1_20261016/high_capacity_candidate_109'
sys.path.insert(0,str(HERE/'deps'))
URL='https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken'
EXPECTED='446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d'
_encoder=None
def encoder():
 global _encoder
 if _encoder is None:
  cache=HERE/'token_cache';file=cache/hashlib.sha1(URL.encode()).hexdigest()
  if not file.exists()or hashlib.sha256(file.read_bytes()).hexdigest()!=EXPECTED:raise ValueError('Verified local tokenizer table unavailable; no network fallback')
  os.environ['TIKTOKEN_CACHE_DIR']=str(cache)
  import tiktoken
  _encoder=tiktoken.get_encoding('o200k_base')
 return _encoder
def quota_tokens(body):
 output=body.get('max_output_tokens',body.get('max_completion_tokens'))
 if type(output)is not int or output<=0:raise ValueError('Complete output limit required')
 # Includes messages, full JSON schema and all serialized fields; local encoding
 # is a proxy for Luna, not a model-specific exact count. Keep 30% + 8192 margin.
 count=len(encoder().encode(json.dumps(body,ensure_ascii=False),disallowed_special=()))
 return math.ceil(count*1.30)+8192+output
