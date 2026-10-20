"""Seal deliverable hashes and append-only ledger snapshot metadata; no API."""
from pathlib import Path
from collections import Counter
from hashlib import sha256
import json
from .night_validation import AUTH,ROOT,accounting
from .run_authorized_validation import save

def run(target):
    target=Path(target)
    ledger=ROOT/'ledger.jsonl';raw=ledger.read_bytes()
    events=[json.loads(line) for line in raw.decode('utf-8').splitlines()]
    reserved={row['attempt']:row for row in events if row['kind']=='reserved' and row['authorization']==AUTH['authorization_id']}
    settled={row['attempt']:row for row in events if row['kind']=='settled' and row['attempt'] in reserved}
    save(target/'api_accounting.json',{'authorization_id':AUTH['authorization_id'],'accounting':accounting(),
        'ledger_path':str(ledger),'ledger_sha256':sha256(raw).hexdigest(),'ledger_events':len(events),
        'reserved_models':dict(Counter(row['model'] for row in reserved.values())),
        'unsettled_attempts':[row for key,row in reserved.items() if key not in settled],
        'original_night_attempts_already_present':2,'new_reserved_attempts':len(reserved)-2,
        'ledger_policy':'Original ledger retained append-only; no uncertain reserve released; no CRISIS funds.'})
    save(target/'files_delivery.json',[{'path':str(path),'bytes':path.stat().st_size,'sha256':sha256(path.read_bytes()).hexdigest()}
        for path in target.rglob('*') if path.is_file()])

if __name__=='__main__':
    import sys
    run(sys.argv[1])
