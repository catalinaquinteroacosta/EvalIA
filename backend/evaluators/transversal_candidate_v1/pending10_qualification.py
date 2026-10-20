"""Bind reviewed focal qualification to the exact official reader and contract."""
from copy import deepcopy
from crisis_semantic.span_provider import SpanProvider,MODEL
from .pending10_provider import Pending10Provider

def bind_qualification(provider,code,proof,definitions):
    provider.qualified_components.discard(code)
    if code not in ('CR-RI2','CR-CE10'):raise ValueError('unexpected_qualification_component')
    if (not isinstance(provider,SpanProvider) or provider.model!=MODEL
            or getattr(provider.run,'__func__',None) is not SpanProvider.run):
        raise ValueError('qualification_reader_identity_mismatch')
    if proof.get('identity')!=Pending10Provider.qualification_identity(definitions):
        raise ValueError('qualification_contract_or_protocol_mismatch')
    if code=='CR-CE10':
        provider.accept_ce10_qualification(proof,definitions)
        return
    # RI2's technical hold affects level 1 specifically. Its current literal
    # direction predicate must be tested with that held anchor, not an old seed.
    cases=proof.get('cases',[])
    if len(cases)!=1 or cases[0].get('expected')!=1 or cases[0].get('actual')!=1:
        raise ValueError('ri2_held_level_not_qualified')
    case=cases[0]
    if case.get('descriptor_review_passed') is not True:
        raise ValueError('qualification_descriptor_review_missing')
    readings=case.get('readings',[])
    if len(readings)!=2 or {r.get('stage') for r in readings}!={'extract','verify'}:
        raise ValueError('qualification_blind_pair_missing')
    if len({r.get('request_digest') for r in readings})!=2 or any(
        r.get('model')!=MODEL or not r.get('response_path') or not r.get('request_digest')
        or r.get('reviewed_entire_context') is not True
        or r.get('literal_and_provenance_passed') is not True for r in readings):
        raise ValueError('qualification_evidence_invalid')
    provider.qualification_records[code]=deepcopy(proof)
    provider.qualified_components.add(code)
