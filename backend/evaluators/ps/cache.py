"""Private content-addressed cache. Never reuse blocked, errors, or ambiguous payloads."""
import hashlib
import json
from pathlib import Path

CACHE_VERSION = 'PS-CACHE-1'

def key_for(stage: str, *, code: str, model: str, system: str, payload: dict, rubric: dict, schema: str = 'ps-json-v1') -> str:
    if stage not in ('extract','verify','reconcile'):
        raise ValueError('Unknown stage')
    record={'version':CACHE_VERSION,'stage':stage,'code':code,'model':model,'system':system,'payload':payload,'rubric':rubric,'schema':schema}
    return hashlib.sha256(json.dumps(record,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

class PrivateCache:
    def __init__(self, directory: str | Path):
        self.directory=Path(directory)
    def read(self, key: str):
        if len(key)!=64 or any(c not in '0123456789abcdef' for c in key): raise ValueError('Invalid cache key')
        path=self.directory/(key+'.json')
        if not path.is_file(): return None
        try:
            obj=json.loads(path.read_text(encoding='utf-8'))
        except (ValueError,OSError): return None
        if not isinstance(obj,dict) or obj.get('cache_key')!=key or obj.get('status')!='verified': return None
        return obj.get('result') if isinstance(obj.get('result'),dict) else None
    def write_verified(self, key: str, result: dict):
        if not isinstance(result,dict): raise TypeError('Expected dict')
        if any(x in json.dumps(result).lower() for x in ('"blocked"','"ambiguous"','"error"')):
            raise ValueError('Do not cache blocked/ambiguous/error')
        self.directory.mkdir(parents=True,exist_ok=True)
        path=self.directory/(key+'.json')
        tmp=self.directory/(key+'.tmp')
        tmp.write_text(json.dumps({'cache_key':key,'status':'verified','result':result},ensure_ascii=False),encoding='utf8')
        tmp.replace(path)
