"""IR DOCX route: two blind component readings and deterministic Python."""
from backend.evaluators.ansiedad_semantic.functional_review import prompt, adjudicate
from backend.evaluators.nd.contracts import TurnContext, HistoryTurn
from .semantic import ask_openai


def evaluate_level(ctx, code, components):
    # Compatibility name only. No ordinal classification is requested.
    if not isinstance(components, list) or not components:
        raise ValueError("Componentes no disponibles")
    if any(item.get("status") not in ("supported", "absent_verified") for item in components):
        return {"status":"BLOCKED", "verified_level":None,"reason":"Componentes previos sin verificar"}
    context = TurnContext(ctx.user,ctx.response,tuple(HistoryTurn(m.role,m.text) for m in ctx.prior_history))
    try:
        extraction = ask_openai("Extrae componentes; no asignes niveles.", {"request":prompt(code,context,"extract")})
        verification = ask_openai("Verifica independientemente los originales sin conocer otra lectura; no asignes niveles.", {"request":prompt(code,context,"independent_verify")})
        decision = adjudicate(code,context,extraction,verification)
    except (ValueError,TypeError,KeyError,RuntimeError,OSError) as error:
        return {"status":"BLOCKED","verified_level":None,"reason":str(error)}
    if decision["status"] != "SCORED":
        return {**decision,"verified_level":None}
    # Labels are derived only here after Python has applied the DOCX rule.
    label = {0:"absent",1:"low",2:"adequate",3:"high"}[decision["score"]]
    evidence = [e for r in decision["reviews"] for e in r["evidence"]]
    return {**decision,"status":"VERIFIED","verified_level":label,
            "evidence":evidence,"verification_evidence":evidence,"evidence_valid":True,
            "rule_version":"IR-DOCX-COMPONENTS-20261012-1"}
