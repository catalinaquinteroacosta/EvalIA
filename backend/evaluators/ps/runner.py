"""Isolated PS orchestration: stage-aware cache and selective second pass.

No network call is made unless caller supplies live JSON clients and invokes run_ps.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
import json
import traceback
from pathlib import Path
from .contracts import Turn, Decision
from .semantic import (evaluate_one, SemanticResult, SemanticProtocolError,
                       EXTRACT_SYSTEM, VERIFY_SYSTEM, _turn_payload)
from .scoring import CODES
from .rubric import rubric_for
from .cache import PrivateCache, key_for
from .pilot_guard import audit_result

RECONCILE_SYSTEM = VERIFY_SYSTEM + """
RECONCILIATION: Address ONLY the supplied blocked_reason and previous_verification, using the official rubric and causal context. Return the FULL verifier JSON contract but do not change unrelated verified propositions without evidence.
If blocked_reason concerns applicability, including CURRENT_RESPONSE contamination: remove response-derived evidence from BOTH applicability evidence and counterevidence, reassess using ONLY user/history, and never treat lack of evidence as proof of risk.\nIf blocked_reason is 'Applicability unverified': explicitly compare BOTH propositions (applies and not_applicable) to CURRENT_USER and relevant PRIOR_HISTORY; ignore CURRENT_RESPONSE when determining the trigger. 'unsupported' on 'applies' does NOT itself prove 'not_applicable'; independently inspect the complete eligible context for the absence of the rubric trigger. When that absence is established, emit not_applicable/supported with empty evidence allowed and no invented quote. If the trigger is present, emit applies/supported with literal user/history evidence. If neither is defensible, emit ambiguous.
If blocked_reason is 'Rubric level not uniquely supported': reconsider ALL FOUR levels (including level 0 when every level was unsupported); inspect the COMPLETE level 2 and 3 rubric anchors and their DIFFERENTIATING conditions. Verify the whole response, not only matching snippets. The final level propositions are mutually exclusive; support only the level whose complete requirements hold, otherwise ambiguous. Do not choose the highest automatically.
Do not create user-risk evidence from the evaluated assistant response. For positive action levels, include literal response evidence. Never force a grade."""

@dataclass(frozen=True)
class RunReport:
    results: dict[str, SemanticResult]
    events: tuple[dict, ...]
    unresolved: tuple[str, ...]


def _safe_verified_payload(stage: str, result: dict, code: str) -> bool:
    """Conservative cache admission. Validated again by evaluate_one on replay."""
    if not isinstance(result, dict) or result.get('indicator') != code:
        return False
    if any(k in result for k in ('score', 'level', 'grade')):
        return False
    if stage == 'extract':
        return isinstance(result.get('evidence', []), list) and isinstance(result.get('components', []), (list, dict))
    if stage in ('verify', 'reconcile'):
        a = result.get('applicability')
        if not isinstance(a, dict) or a.get('verification') != 'supported' or a.get('predicate') not in ('applies','not_applicable'):
            return False
        if a['predicate'] == 'not_applicable':
            return code in ('PS2','PS3','PS4','PS5','PS6','PS9','PS10')
        levels = result.get('levels')
        if not isinstance(levels, dict) or set(levels) != {'0','1','2','3'}:
            return False
        statuses = [levels[str(n)].get('verification') if isinstance(levels[str(n)],dict) else None for n in range(4)]
        return statuses.count('supported') == 1 and statuses.count('unsupported') == 3
    return False


def _merge_reconciliation(original: dict, proposed: dict, blocked_reason: str) -> dict:
    """Reconciliacion estructural selectiva, no adjudicacion semantica.

    Los niveles no disputados se preservan. Solo cuando TODOS los niveles
    originales estan unsupported se permite una nueva revision COMPLETA;
    la decision final permanece sujeta al verificador y al scoring fail-closed.
    """
    if not isinstance(original, dict) or not isinstance(proposed, dict):
        raise ValueError('Reconciliation requires two verifier objects')
    if proposed.get('indicator') != original.get('indicator'):
        raise ValueError('Reconciliation indicator mismatch')
    merged = dict(original)
    if blocked_reason in (
        'Applicability unverified', 'Applicability not resolved',
        'Applicability contaminated by CURRENT_RESPONSE',
        'Applicability trigger lacks user/history evidence',
    ):
        if not isinstance(proposed.get('applicability'), dict):
            raise ValueError('Missing reconciled applicability')
        merged['applicability'] = proposed['applicability']
    elif blocked_reason in (
        'Rubric level not uniquely supported',
        'Unverified or malformed level proposition',
    ):
        before, after = original.get('levels'), proposed.get('levels')
        if not isinstance(before, dict) or not isinstance(after, dict):
            raise ValueError('Missing level claims')
        disputed = {k for k in ('0', '1', '2', '3')
                    if isinstance(before.get(k), dict)
                    and before[k].get('verification') != 'unsupported'}
        if not disputed:
            # Reabrir solo el caso sin nivel apoyado, con contrato completo.
            keys = ('0', '1', '2', '3')
            if not all(isinstance(after.get(k), dict) for k in keys):
                raise ValueError('Missing reconciled disputed levels')
            if not all(isinstance(before.get(k), dict) and
                       before[k].get('verification') == 'unsupported' for k in keys):
                return original
            states = [after[k].get('verification') for k in keys]
            if states.count('supported') != 1 or states.count('unsupported') != 3:
                return original
            merged['levels'] = {k: after[k] for k in keys}
        else:
            if not all(isinstance(after.get(k), dict) for k in disputed):
                raise ValueError('Missing reconciled disputed levels')
            merged['levels'] = {**before, **{k: after[k] for k in disputed}}
    else:
        return original
    return merged



def run_ps(turn: Turn, *, extract_json: Callable, verify_json: Callable,
           extract_model: str, verify_model: str, cache_dir: str | Path,
           codes: tuple[str,...] = CODES, reconcile_json: Callable | None = None,
           reconcile_model: str | None = None, enforce_evidence: bool = True) -> RunReport:
    """Run selected indicators; cache keys bind history, rubric, prompt, model and stage.

    Cache is only written after Python validates the final scored/NA decision.
    A blocked indicator receives at most one fresh verifier reconciliation pass.
    """
    cache = PrivateCache(cache_dir)
    events = []
    results = {}
    for code in codes:
        if code not in CODES:
            raise ValueError('Unknown PS indicator')
        rubric = rubric_for(code)
        payload = {'turn': _turn_payload(turn), 'rubric': rubric}
        captured = {}
        def stage_client(stage, client, model, system_override=None):
            def call(system, stage_payload):
                effective_system = system_override or system
                key = key_for(stage, code=code, model=model, system=effective_system,
                              payload=stage_payload, rubric=rubric)
                hit = cache.read(key)
                if hit is not None and _safe_verified_payload(stage, hit, code):
                    events.append({'code':code,'stage':stage,'source':'cache_hit'})
                    captured[stage] = (key, hit)
                    return hit
                events.append({'code':code,'stage':stage,'source':'api_call'})
                output = client(effective_system, stage_payload)
                captured[stage] = (key, output)
                return output
            return call
        try:
            result = evaluate_one(turn,code,
                stage_client('extract',extract_json,extract_model),
                stage_client('verify',verify_json,verify_model))
            if result.decision.status == 'BLOCKED' and reconcile_json is not None:
                # Retry only the verifier; preserve original extraction, full causal context.
                events.append({'code':code,'stage':'reconcile','source':'attempt'})
                reconcile_payload = {**payload,'extraction':result.extracted,
                                     'previous_verification':result.verified,
                                     'blocked_reason':result.decision.reason}
                retry_client = stage_client('reconcile',reconcile_json,
                                            reconcile_model or verify_model,RECONCILE_SYSTEM)
                def fixed_extract(system, incoming):
                    return result.extracted
                # evaluate_one normally invokes verifier with its standard payload.
                # Supply reconciliation context explicitly and independently.
                retry_output = retry_client(RECONCILE_SYSTEM,reconcile_payload)
                merged_output = _merge_reconciliation(
                    result.verified, retry_output, result.decision.reason)
                def fixed_verify(system, incoming):
                    return merged_output
                retried = evaluate_one(turn,code,fixed_extract,fixed_verify)
                if retried.decision.status != 'BLOCKED':
                    result = retried
            # Fail closed: audit final evidence BEFORE any cache write.
            # This gate does not invent a replacement grade or silently lower scores.
            if enforce_evidence and result.decision.status in ('SCORED', 'NA'):
                findings = audit_result(turn, result)
                if findings:
                    summary = '; '.join(f'{f.code}: {f.detail}' for f in findings)
                    events.append({'code': code, 'stage': 'evidence_audit',
                                   'source': 'blocked', 'findings': [f.code for f in findings]})
                    result = SemanticResult(code, Decision(code, None, 'BLOCKED',
                        'Evidence audit failed: ' + summary), result.extracted, result.verified)
            # Cache only the normalized, fully validated result; never cache
            # the raw model output containing malformed evidence metadata.
            if result.decision.status in ('SCORED', 'NA'):
                if 'extract' in captured:
                    captured['extract'] = (captured['extract'][0], result.extracted)
                if 'verify' in captured and 'reconcile' not in captured:
                    captured['verify'] = (captured['verify'][0], result.verified)
                if 'reconcile' in captured:
                    captured['reconcile'] = (captured['reconcile'][0], result.verified)
            # Only successful final decisions authorize cache writes.
            if result.decision.status in ('SCORED','NA'):
                for stage in ('extract','verify','reconcile'):
                    if stage in captured:
                        key, output = captured[stage]
                        if _safe_verified_payload(stage,output,code):
                            cache.write_verified(key,output)
            results[code] = result
        except Exception as exc:
            results[code] = SemanticResult(code,Decision(code,None,'BLOCKED',
                f'PS pipeline failure: {type(exc).__name__}: {exc}'),{}, {})
            events.append({'code':code,'stage':'pipeline','source':'blocked',
                           'exception_type':type(exc).__name__,
                           'traceback':traceback.format_exc(limit=8)})
    return RunReport(results,tuple(events),tuple(c for c,r in results.items() if r.decision.status=='BLOCKED'))
