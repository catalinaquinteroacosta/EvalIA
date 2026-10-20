"""Literal verification and independent semantic reconciliation, with audit trails."""
from .domain import Input

class EvidenceError(ValueError):
    pass

def validate_payload(payload, expected_ids):
    if not isinstance(payload, dict) or set(payload) != {"reviewed_entire_context", "claims"}:
        raise EvidenceError("invalid_semantic_envelope")
    if type(payload["reviewed_entire_context"]) is not bool or not isinstance(payload["claims"], list):
        raise EvidenceError("invalid_semantic_types")
    found = []
    for claim in payload["claims"]:
        if not isinstance(claim, dict) or set(claim) != {"id", "state", "citations", "reason"}:
            raise EvidenceError("invalid_claim_fields")
        if claim["state"] not in ("yes", "no", "unknown") or not isinstance(claim["reason"], str) or not claim["reason"].strip():
            raise EvidenceError("invalid_claim_state_or_reason")
        if not isinstance(claim["citations"], list) or len(claim["citations"]) > 4:
            raise EvidenceError("invalid_citations")
        for citation in claim["citations"]:
            if not isinstance(citation, dict) or set(citation) != {"source", "history_index", "quote"}:
                raise EvidenceError("invalid_citation_fields")
            if citation["source"] not in ("current_user", "current_ai", "prior_user", "prior_ai") or not isinstance(citation["quote"], str):
                raise EvidenceError("invalid_citation_type")
        found.append(claim["id"])
    if len(found) != len(set(found)) or set(found) != set(expected_ids):
        raise EvidenceError("missing_duplicate_or_unrequested_claims")
    return payload

def literal_check(claim, definition, context: Input, reviewed, external_attestations):
    errors = []
    for citation in claim["citations"]:
        try:
            text = context.text(citation["source"], citation["history_index"])
            if not citation["quote"] or citation["quote"] not in text:
                errors.append("nonliteral_quote")
        except ValueError as exc:
            errors.append(str(exc))
    if claim["state"] == "yes":
        if not claim["citations"]:
            errors.append("positive_without_evidence")
        if definition["kind"] == "response" and not any(c["source"] == "current_ai" for c in claim["citations"]):
            errors.append("current_response_not_evidenced")
        if definition.get("code") == "CR-CE10" and definition["kind"] == "response" and not any(c["source"] in ("prior_user", "prior_ai") for c in claim["citations"]):
            errors.append("longitudinal_context_not_evidenced")
    if claim["state"] == "no" and not reviewed:
        errors.append("absence_without_full_context_review")
    if definition["external_required"] and claim["state"] == "yes" and claim["id"] not in external_attestations:
        errors.append("external_verification_missing")
    return errors

def reconcile(extraction, verification, definitions, context, external_attestations=()):
    validate_payload(extraction, definitions)
    validate_payload(verification, definitions)
    left = {c["id"]: c for c in extraction["claims"]}
    right = {c["id"]: c for c in verification["claims"]}
    values, decisions, issues = {}, {}, []
    for key, definition in definitions.items():
        a, b = left[key], right[key]
        errors = literal_check(a, definition, context, extraction["reviewed_entire_context"], external_attestations)
        errors += literal_check(b, definition, context, verification["reviewed_entire_context"], external_attestations)
        if a["state"] != b["state"]:
            errors.append("independent_semantic_disagreement")
        if a["state"] == "unknown" or b["state"] == "unknown":
            errors.append("semantic_uncertainty")
        values[key] = None if errors else a["state"] == "yes"
        decisions[key] = {"value": values[key], "extraction": a, "verification": b, "issues": sorted(set(errors))}
        issues.extend({"id": key, "cause": error} for error in sorted(set(errors)))
    return values, decisions, issues

def literal_spans(text):
    """Structural segmentation only; never detects constructs or assigns scores.

    Every candidate is an exact substring. Punctuation is retained. The model
    selects evidence; Python does not infer semantics from these boundaries.
    """
    spans, start = [], 0
    for index, character in enumerate(text):
        if character in ".!?;\n":
            span = text[start:index + 1].strip()
            if span:
                spans.append(span)
            start = index + 1
    tail = text[start:].strip()
    if tail:
        spans.append(tail)
    return list(dict.fromkeys(spans))


def output_schema(ids, context=None):
    def citation_branch(sources, index):
        return {"type": "object", "properties": {"source": {"type": "string", "enum": sources}, "history_index": index, "quote": {"type": "string"}}, "required": ["source", "history_index", "quote"], "additionalProperties": False}
    branches = [citation_branch(["current_user", "current_ai"], {"type": "null"}), citation_branch(["prior_user", "prior_ai"], {"type": "integer"})]
    if context is not None:
        branches = []
        sources = [("current_user", None), ("current_ai", None)]
        sources.extend((source, index) for index in range(len(context.history)) for source in ("prior_user", "prior_ai"))
        for source, index in sources:
            spans = literal_spans(context.text(source, index))
            if not spans:
                continue
            branch = citation_branch([source], {"type": "null"} if index is None else {"type": "integer", "enum": [index]})
            branch["properties"]["quote"]["enum"] = spans
            branches.append(branch)
    citation = {"anyOf": branches}
    claim = {"type": "object", "properties": {"state": {"type": "string", "enum": ["yes", "no", "unknown"]}, "citations": {"type": "array", "items": {"$ref": "#/$defs/citation"}}, "reason": {"type": "string"}}, "required": ["state", "citations", "reason"], "additionalProperties": False}
    # A required property per predicate prevents omissions/duplicates in long batches.
    return {"type": "object", "$defs": {"claim": claim, "citation": citation}, "properties": {"reviewed_entire_context": {"type": "boolean"}, "claims": {"type": "object", "properties": {key: {"$ref": "#/$defs/claim"} for key in ids}, "required": list(ids), "additionalProperties": False}}, "required": ["reviewed_entire_context", "claims"], "additionalProperties": False}

def canonical_payload(payload):
    if isinstance(payload, dict) and isinstance(payload.get("claims"), dict):
        return {**payload, "claims": [{"id": key, **value} for key, value in payload["claims"].items()]}
    return payload
