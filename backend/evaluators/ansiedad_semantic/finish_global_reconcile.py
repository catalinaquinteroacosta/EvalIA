"""Conservative global cash reconciliation; no uncertain reservation is released."""
from decimal import Decimal
import json
from .night_validation import AUTH,ROOT
from .run_authorized_validation import save
from .budgeted_reader import Reader

def run():
    old=json.loads((ROOT/'balance_checkpoint_20261013.json').read_text(encoding='utf-8'))
    events=[json.loads(line) for line in (ROOT/'ledger.jsonl').read_text(encoding='utf-8').splitlines()]
    settled={row['attempt'] for row in events if row['kind']=='settled'}
    pending=[row for row in events if row['kind']=='reserved' and row['attempt'] not in settled]
    other=sum((Decimal(row['reserved_usd']) for row in pending if row['authorization']!=AUTH['authorization_id']),Decimal(0))
    crisis_hold=Decimal('0.5733136')
    cap=Decimal(old['accounting_at_checkpoint']['actual_usd'])+Decimal(old['reported_remaining_balance_usd'])-other-crisis_hold
    record={**old,'authority':'Global reserve reconciliation of the same user-reported USD5; not a new balance or authorization.',
        'original_checkpoint_path':str(ROOT/'balance_checkpoint_20261013.json'),
        'other_anxiety_uncertain_reserves_usd':str(other),'external_crisis_retention_usd':str(crisis_hold),
        'external_crisis_retention_source':'docs/ansiedad_semantic/live_990_20261012/night_consolidated_05/REPORT_FINAL.md',
        'cumulative_operational_cap_usd':str(cap),
        'policy':'Keep all historical holds. External CRISIS amount is withheld conservatively from account cash, never transferred or spent by anxiety. No further paid calls until cash/holds can be reconciled.'}
    save(ROOT/'balance_checkpoint_20261013_global.json',record)
    Reader(AUTH)._append({'kind':'controller_interruption','authorization':AUTH['authorization_id'],
        'reason':'Stop paid work for global uncertain-reserve reconciliation; managed session interrupt after Stop-Process request rejected.',
        'pending_attempts_retained':[r['attempt'] for r in pending if r['authorization']==AUTH['authorization_id']],
        'no_reserves_released':True})
    print(json.dumps({'other_anxiety_holds_usd':str(other),'external_crisis_retention_usd':str(crisis_hold),'cumulative_operational_cap_usd':str(cap)}))

if __name__=='__main__':run()
