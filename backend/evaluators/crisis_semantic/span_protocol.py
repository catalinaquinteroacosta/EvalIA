"""Compact, source-constrained evidence references; no semantic scoring here."""
from .evidence import literal_spans, EvidenceError

PROTOCOL = "span-observations-2"

def spans(context):
    result = {}
    sources = [("current_user", None), ("current_ai", None)]
    sources.extend((source, index) for index in range(len(context.history)) for source in ("prior_user", "prior_ai"))
    for source, index in sources:
        for number, quote in enumerate(literal_spans(context.text(source, index))):
            key = f"{source}:{index}:{number}"
            result[key] = {"source": source, "history_index": index, "quote": quote}
    return result

def schema(defs, library):
    all_ids = list(library)
    response_ids = [key for key, span in library.items() if span["source"] == "current_ai"]
    context_ids = [key for key, span in library.items() if span["source"] != "current_ai"]
    def observations(evidence_ids):
        branches = []
        for state in ("present", "absent", "uncertain"):
            evidence = {"type": "array", "items": {"type": "string", "enum": evidence_ids}, "maxItems": 2}
            if state == "present":
                evidence["minItems"] = 1
            branches.append({"type": "object", "properties": {"observation": {"type": "string", "enum": [state]}, "evidence": evidence,
                "context": {"type": "array", "items": {"type": "string", "enum": context_ids}, "maxItems": 2}, "reason": {"type": "string"}},
                "required": ["observation", "evidence", "context", "reason"], "additionalProperties": False})
        return {"anyOf": branches}
    return {"type": "object", "$defs": {"response": observations(response_ids), "context": observations(all_ids)},
        "properties": {"reviewed_entire_context": {"type": "boolean"}, "claims": {"type": "object", "properties": {key: {"$ref": "#/$defs/" + ("response" if value["kind"] == "response" else "context")} for key,value in defs.items()}, "required": list(defs), "additionalProperties": False}},
        "required": ["reviewed_entire_context", "claims"], "additionalProperties": False}

def decode(wire, library, defs):
    if not isinstance(wire, dict) or set(wire) != {"reviewed_entire_context", "claims"} or not isinstance(wire["claims"], dict) or set(wire["claims"]) != set(defs):
        raise EvidenceError("invalid_span_envelope")
    claims = []
    for key, value in wire["claims"].items():
        if not isinstance(value, dict) or set(value) != {"observation", "evidence", "context", "reason"}:
            raise EvidenceError("invalid_span_observation")
        state = {"present": "yes", "absent": "no", "uncertain": "unknown"}.get(value["observation"])
        if state is None or any(not isinstance(value[name], list) or len(value[name]) > 2 for name in ("evidence", "context")):
            raise EvidenceError("invalid_span_state")
        if state == "yes" and not value["evidence"]:
            raise EvidenceError("positive_without_evidence")
        citations = []
        for role in ("evidence", "context"):
            for span_id in value[role]:
                if span_id not in library:
                    raise EvidenceError("unknown_span_reference")
                citation = library[span_id]
                if role == "evidence" and defs[key]["kind"] == "response" and citation["source"] != "current_ai":
                    raise EvidenceError("response_support_from_wrong_source")
                if role == "context" and citation["source"] == "current_ai":
                    raise EvidenceError("context_support_from_response")
                citations.append(dict(citation))
        claims.append({"id": key, "state": state, "citations": citations, "reason": value["reason"]})
    return {"reviewed_entire_context": wire["reviewed_entire_context"], "claims": claims}
