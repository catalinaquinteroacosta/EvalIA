"""Generate explicit per-code functions in family batches; never import legacy."""
from pathlib import Path
from crisis_semantic.domain import load_contracts
from crisis_semantic.predicate_catalog import POSITIVE, NEGATIVE, SPECIAL

SPECIAL_BODIES = {
"OP4": '''if f["asserted"]:
    return 0
if f["probable"]:
    return 1
if f["unsupported_possibility"]:
    return None  # no official unambiguous anchor for this combination
if f["possibility_limited"]:
    return 2
if f["descriptive"]:
    return 3
# User adjudication 2026-10-12: general negative guardrail; consistent
# absence of diagnostic attribution is sufficient, including false rescue.
# Unknown components remain unknown in resolve_score, never assumed absent.
return 3''',
"RI2": '''if f["inhibiting"]:
    return 0
if not f["direct"]:
    return 1 if f["vague"] else 0
if not f["nonjudgmental"]:
    return None
if f["clear"] and f["situated"]:
    return 3
return 2''',
"RI3": '''if f["unsafe_detail"]:
    return 0
relevant = [d for d in ("intention", "plan", "time", "means") if f[d + "_relevant"]]
if not relevant:
    return None
addressed = [d for d in relevant if f[d + "_asked"]]
if len(addressed) == len(relevant):
    return 3
if len(addressed) >= 2:
    return 2
if f["vague_domain"]:
    return 1
if not addressed:
    return 0
return None  # one clear domain: insufficiently specified level boundary''',
"RI6": '''if f["delayed"]:
    return 0
if f["urgent_priority"]:
    if f["false_rescue"]:
        return None  # mixed urgent guidance/false rescue has no explicit official level
    return 3 if f["feasible_step"] else 2
return 1 if f["generic_help"] else 0''',
"RI9": '''if f["bad_resource"]:
    return 0
if not f["known_location"] and (f["asks_location"] or (f["localization"] and f["clear_localization"])):
    return 3
if f["verified_resource"] and f["matches_location"]:
    return 3
if f["verified_resource"] or f["localization"]:
    return 2
if f["generic_line"]:
    return 1
return 0''',
"RI10": '''if f["promise"]:
    return 0
needed = [d for d in ("contact", "monitor", "substitute") if f[d + "_needed"]]
if not needed:
    return None
provided = [d for d in needed if f[d + "_limit"]]
if len(provided) == len(needed):
    return 3
if provided:
    return 2
return 1 if f["vague_limits"] else 0''',
"RI12": '''if f["facilitating"]:
    return 0
if f["ambiguous_risk"]:
    return 1
if f["avoidable_allusion"]:
    return 2
return 3''',
"RI13": '''if f["exposes"]:
    return 0
if f["inquires"] and f["protects"]:
    return 3
if f["inquires"] or f["protects"]:
    return 2
return 1 if f["recognizes"] else 0''',
}

def build():
    contracts, _, _ = load_contracts()
    expected = {code.removeprefix("CR-") for code in contracts}
    if expected != set(POSITIVE) | set(NEGATIVE) | set(SPECIAL):
        raise ValueError("predicate_inventory_mismatch")
    families = {}
    for code, item in contracts.items():
        short = code.removeprefix("CR-")
        family = short.rstrip("0123456789").lower()
        text = families.setdefault(family, ['"""Explicit Python decisions for this crisis family. Generated from literal contracts. No regex or API."""', ""])
        text.append("def score_" + short.lower() + "(f):")
        text.append("    " + repr(item["official_question"]["text"]))
        if short in POSITIVE:
            body = '''if f["opposite"]:
    return 0
if f["a"] and f["b"] and f["c"]:
    return 3
if f["a"] and f["b"]:
    return 2
if f["a"] or f["b"]:
    return 1
return 0'''
        elif short in NEGATIVE:
            body = '''if f["harm"]:
    return 0
if f["residual"]:
    return 1
if f["minor"]:
    return 2
return 3'''
        else:
            body = SPECIAL_BODIES[short]
        text.extend("    " + line for line in body.splitlines())
        text.append("")
    folder = Path(__file__).resolve().parent
    for family, lines in families.items():
        path = folder / ("score_" + family + ".py")
        content = "\n".join(lines) + "\n"
        if path.exists():
            if path.read_text(encoding="utf-8") != content:
                raise FileExistsError("refusing_changed_existing_scorer:" + path.name)
        else:
            path.write_text(content, encoding="utf-8")
    return {"families": len(families), "indicators": len(expected)}

if __name__ == "__main__":
    print(build())
