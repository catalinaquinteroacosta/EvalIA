"""Explicit local reconciliation of NEW instrumented attempts only. No HTTP.
Does not apply retrospectively to 123/262: their no-send proof is absent.
"""
import json,hashlib
from pathlib import Path
def reconcile(folder):
    from backend.luna_application import request_key
    from backend.luna_budget import BudgetJournal
    folder=Path(folder);auth=json.loads((folder/'authorization.json').read_text(encoding='utf8'));mp=Path(auth['manifest_path']);raw=mp.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=auth['sealed_manifest_sha256']:raise ValueError('manifest changed')
    rows=json.loads(raw)['requests']
    if len(rows)!=1:raise ValueError('single attempt required')
    key,wire=request_key(rows[0]['body'],rows[0]['endpoint'])
    if (folder/(key+'.request.json')).read_bytes()!=wire:raise ValueError('request changed')
    phases=[json.loads(line) for line in (folder/(key+'.transport.jsonl')).read_text(encoding='utf8').splitlines()]
    failure=json.loads((folder/(key+'.failure.json')).read_text(encoding='utf8'))
    if not phases or any(p['identity']!=key or p['phase'] in ('api_dispatch_started','headers_received','body_received') for p in phases):raise ValueError('not proved unsent')
    if phases[-1].get('classification')!='confirmed_no_api_send' or failure.get('classification')!='confirmed_no_api_send':raise ValueError('uncertain attempt stays reserved')
    if any((folder/(key+'.'+s+'.json')).exists() for s in ('headers','response','receipt')):raise ValueError('response evidence present; use receipt reconciliation')
    journal=BudgetJournal(auth['budget_journal']);journal.settle(auth['run_id'],actual_usd='0',actual_requests=0,usage_evidence=str(folder/(key+'.transport.jsonl')),fully_reconciled=True)
    # No semantic receipt/result is fabricated. The failed attempt is retained.
    return dict(classification='confirmed_no_api_send',actual_usd='0',actual_requests=0,semantic_result=None)
