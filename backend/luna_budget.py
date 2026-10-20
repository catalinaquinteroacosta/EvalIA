"""Durable, offline budget journal. No network, SQLite, or spend authorization."""
import json
import os
from decimal import Decimal,InvalidOperation
from hashlib import sha256
from pathlib import Path
from uuid import uuid4
from backend.luna_application import ProcessLock


class BudgetBlocked(RuntimeError):
    pass


def money(value):
    if isinstance(value,bool):raise ValueError('invalid_money')
    try:amount=Decimal(str(value))
    except (InvalidOperation,TypeError,ValueError):raise ValueError('invalid_money') from None
    if not amount.is_finite() or amount<0:raise ValueError('invalid_money')
    return amount


def count(value,positive=False):
    if type(value) is not int or value<(1 if positive else 0):raise ValueError('invalid_request_count')
    return value


def fingerprint(value):
    return sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


class BudgetJournal:
    """A reservation must precede transmission; caller owns actual API execution.

    Uncertain submissions remain reserved until reconciled from real usage.
    A balance is never permission. This guard cannot authorize the definitive950.
    """
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.lock=ProcessLock(self.path.with_suffix(self.path.suffix+'.lock'))

    def initialize(self,*,cap_usd='100',prior_spent_usd='0',prior_evidence):
        cap=money(cap_usd);prior=money(prior_spent_usd)
        if cap<=0 or cap>100 or prior>cap or not isinstance(prior_evidence,str) or not prior_evidence.strip():raise ValueError('invalid_initial_budget')
        genesis=dict(cap_usd=str(cap),prior_spent_usd=str(prior),prior_evidence=prior_evidence)
        with self.lock:
            if self.path.exists():
                state=self._load()
                if state['genesis']!=genesis:raise BudgetBlocked('initial_budget_mismatch_no_reset')
                return self._totals(state)
            state=dict(version=1,genesis=genesis,entries={},blocked_reasons=[])
            self._write(state);return self._totals(state)

    def _load(self):
        if not self.path.exists():raise BudgetBlocked('budget_not_initialized')
        try:
            state=json.loads(self.path.read_text(encoding='utf-8'))
            if state['version']!=1 or not isinstance(state['entries'],dict) or not isinstance(state['blocked_reasons'],list):raise ValueError()
            cap=money(state['genesis']['cap_usd']);prior=money(state['genesis']['prior_spent_usd'])
            if cap<=0 or cap>100 or prior>cap or not state['genesis']['prior_evidence']:raise ValueError()
            for run,row in state['entries'].items():
                if row['run_id']!=run or row['status'] not in ('reserved','uncertain','settled'):raise ValueError()
                money(row['reservation_usd']);count(row['requests'],True)
                if row['status']=='settled':money(row['actual_usd']);count(row['actual_requests'])
            return state
        except (ValueError,KeyError,TypeError):raise BudgetBlocked('budget_journal_invalid') from None

    def _write(self,state):
        temporary=self.path.with_name(self.path.name+'.'+uuid4().hex+'.tmp')
        try:
            with temporary.open('x',encoding='utf-8') as stream:
                json.dump(state,stream,ensure_ascii=False,indent=2);stream.flush();os.fsync(stream.fileno())
            os.replace(temporary,self.path)
        finally:
            if temporary.exists():temporary.unlink()

    def _totals(self,state):
        spent=money(state['genesis']['prior_spent_usd']);reserved=Decimal(0);pending=0;actual_requests=0
        for row in state['entries'].values():
            if row['status']=='settled':spent+=money(row['actual_usd']);actual_requests+=count(row['actual_requests'])
            else:reserved+=money(row['reservation_usd']);pending+=count(row['requests'])
        cap=money(state['genesis']['cap_usd'])
        return dict(cap_usd=str(cap),spent_usd=str(spent),reserved_usd=str(reserved),available_usd=str(cap-spent-reserved),pending_requests=pending,actual_requests=actual_requests,blocked=bool(state['blocked_reasons']),blocked_reasons=list(state['blocked_reasons']),authorization_granted_by_balance=False)

    def snapshot(self):
        with self.lock:return self._totals(self._load())

    def reserve(self,run_id,manifest_sha256,*,reservation_usd,requests,authorization,scope,definitive_950=False):
        amount=money(reservation_usd);requests=count(requests,True)
        if amount<=0:raise ValueError('positive_reservation_required')
        if not isinstance(run_id,str) or not run_id.strip() or not isinstance(scope,str) or not scope.strip():raise ValueError('missing_run_or_scope')
        if not isinstance(manifest_sha256,str) or len(manifest_sha256)!=64 or any(c not in '0123456789abcdef' for c in manifest_sha256):raise ValueError('invalid_manifest_hash')
        if definitive_950:raise BudgetBlocked('definitive_950_not_authorized_by_this_guard')
        if authorization.get('explicit_user_approval') is not True or authorization.get('scope')!=scope:raise BudgetBlocked('explicit_scoped_authorization_required')
        if authorization.get('sealed_manifest_sha256')!=manifest_sha256:raise BudgetBlocked('authorization_manifest_mismatch')
        if authorization.get('allow_definitive_950') is not False:raise BudgetBlocked('definitive_scope_must_remain_disabled')
        if money(authorization.get('max_usd',0))<amount or count(authorization.get('max_requests',0))<requests:raise BudgetBlocked('authorization_limit_exceeded')
        identity=dict(run_id=run_id,manifest_sha256=manifest_sha256,reservation_usd=str(amount),requests=requests,scope=scope,authorization_sha256=fingerprint(authorization))
        with self.lock:
            state=self._load();old=state['entries'].get(run_id)
            if old:
                if old['identity']!=identity:raise BudgetBlocked('run_identity_mismatch_no_resend')
                return dict(old)
            if any(e['manifest_sha256']==manifest_sha256 for e in state['entries'].values()):raise BudgetBlocked('manifest_already_reserved_no_duplicate')
            totals=self._totals(state)
            if totals['blocked']:raise BudgetBlocked('budget_globally_blocked')
            if amount>money(totals['available_usd']):raise BudgetBlocked('absolute_budget_exceeded')
            row=dict(**identity,identity=identity,status='reserved',submission_status='not_attested')
            state['entries'][run_id]=row;self._write(state);return dict(row)

    def mark_uncertain(self,run_id,*,reason):
        if not isinstance(reason,str) or not reason.strip():raise ValueError('uncertainty_reason_required')
        with self.lock:
            state=self._load();row=state['entries'][run_id]
            if row['status']=='settled':raise BudgetBlocked('already_reconciled')
            row.update(status='uncertain',uncertainty_reason=reason,submission_status='uncertain')
            self._write(state);return dict(row)

    def settle(self,run_id,*,actual_usd,actual_requests,usage_evidence,fully_reconciled=False):
        actual=money(actual_usd);actual_requests=count(actual_requests)
        if fully_reconciled is not True:raise BudgetBlocked('partial_or_uncertain_usage_must_remain_reserved')
        if not isinstance(usage_evidence,str) or not usage_evidence.strip():raise ValueError('usage_evidence_required')
        with self.lock:
            state=self._load();row=state['entries'][run_id]
            if row['status']=='settled':
                if money(row['actual_usd'])!=actual or row['actual_requests']!=actual_requests or row['usage_evidence']!=usage_evidence:raise BudgetBlocked('settlement_mismatch')
                return self._totals(state)
            violations=[]
            if actual>money(row['reservation_usd']):violations.append('actual_exceeds_reservation:'+run_id)
            if actual_requests>row['requests']:violations.append('actual_requests_exceed_reservation:'+run_id)
            row.update(status='settled',actual_usd=str(actual),actual_requests=actual_requests,usage_evidence=usage_evidence,submission_status='reconciled')
            totals=self._totals(state)
            if money(totals['spent_usd'])+money(totals['reserved_usd'])>money(totals['cap_usd']):violations.append('absolute_budget_exceeded_after_usage')
            state['blocked_reasons'].extend(v for v in violations if v not in state['blocked_reasons'])
            self._write(state)
            if violations:raise BudgetBlocked('usage_recorded_future_spending_blocked')
            return self._totals(state)
