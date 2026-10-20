"""Persist a user-reported account balance ceiling without altering ledger history."""
from decimal import Decimal
from .night_validation import accounting,ROOT
from .run_authorized_validation import save

def run(balance):
    current=accounting();reported=Decimal(balance)
    save(ROOT/'balance_checkpoint_20261013.json',{
        'client_date':'2026-10-13','authority':'User message: nos quedan 5 usd',
        'reported_remaining_balance_usd':str(reported),'accounting_at_checkpoint':current,
        'cumulative_operational_cap_usd':str(Decimal(current['actual_usd'])+reported),
        'policy':'Reported balance is not another authorization; all uncertain and pending reserves count against it. No billing dashboard confirmation.'})
    print(current)

if __name__=='__main__':
    import sys
    run(sys.argv[1])
