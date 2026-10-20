"""Dispatch and uncertainty propagation. Individual family functions decide scores."""
from importlib import import_module
from itertools import product
from .predicate_catalog import definitions

def scorer_for(code):
    short = code.removeprefix("CR-").lower()
    family = short.rstrip("0123456789")
    return getattr(import_module("crisis_semantic.score_" + family), "score_" + short)

def resolve_score(code, values, contracts):
    """Unknown observations are not false. Score only if every completion agrees."""
    names = [key.split(".", 1)[1] for key in definitions(contracts, [code]) if not key.endswith(".gate")]
    unknown = [name for name in names if values.get(name) is None]
    if len(unknown) > 12:
        return None, "insufficient_verified_components"
    function = scorer_for(code)
    outcomes = set()
    for assignment in product((False, True), repeat=len(unknown)):
        filled = {name: values.get(name) for name in names}
        filled.update(zip(unknown, assignment))
        outcomes.add(function(filled))
        if len(outcomes) > 1:
            return None, "unresolved_components_change_official_level"
    score = outcomes.pop()
    return (score, None) if score in (0, 1, 2, 3) else (None, "official_anchor_boundary_pending")
