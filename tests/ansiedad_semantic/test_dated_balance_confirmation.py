from decimal import Decimal
from backend.evaluators.ansiedad_semantic import step5a_continue as finance

def test_current_confirmed_balance_retains_old_holds_without_rededucting_old_charges(monkeypatch):
    es=[{'kind':'reserved','attempt':1,'reserved_usd':'1'},
        {'kind':'settled','attempt':1,'actual_usd':'0.5'},
        {'kind':'reserved','attempt':2,'reserved_usd':'0.7'},
        {'kind':'reserved','attempt':3,'reserved_usd':'0.2'},
        {'kind':'settled','attempt':3,'actual_usd':'0.1'}]
    monkeypatch.setattr(finance,'events',lambda:es)
    monkeypatch.setattr(finance,'read',lambda p:{'event_count':3,'confirmed_balance_usd':'7'})
    assert finance.cash()==Decimal('7')-Decimal('0.7')-Decimal('0.1')-Decimal('0.5733136')
