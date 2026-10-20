"""Executable GD component pipeline; injected reader owns provider and budget.

Unlike the historical gd_level_semantic route, no ordinal conclusion is sent
between readers or accepted as input to the Python rules.
"""
import json
from backend.evaluators.nd.contracts import TurnContext, HistoryTurn
from backend.evaluators.ansiedad_semantic.gd_component_review import batch_prompt, adjudicate
from .gd_schemas import GDResult, Evidence, VerifiedEvidence

VERSION = "GD-DOCX-COMPONENTS-20261012-1"

def run_gd_docx(context, *, reader):
    original = TurnContext(context.current_user,context.current_response,
                           tuple(HistoryTurn(item.role,item.text) for item in context.prior_history))
    try:
        extraction = reader(json.loads(batch_prompt(original,"extract")))
        verification = reader(json.loads(batch_prompt(original,"independent_verify")))
    except Exception as error:
        # A transport failure cannot become a score, and is retained verbatim.
        return {"results":{f"GD{i}":GDResult(f"GD{i}","BLOCKED",None,
                f"{type(error).__name__}: {error}",rule_version=VERSION) for i in range(1,9)},
                "transport_error":f"{type(error).__name__}: {error}"}
    results = {}
    decisions = {}
    for i in range(1,9):
        code = f"GD{i}"
        try:
            a,b = [row["indicators"][code] for row in (extraction,verification)]
            decision = adjudicate(code,original,a,b)
        except (KeyError,TypeError,ValueError) as error:
            decision = {"code":code,"status":"BLOCKED","score":None,"reason":str(error)}
        decisions[code] = decision
        evidence = []
        if decision["status"] == "SCORED":
            for reading in (a,b):
                for component in reading["components"].values():
                    for citation in component["evidence"] + component["counterevidence"]:
                        source={"user":"CURRENT_USER","response":"CURRENT_RESPONSE","history":"PRIOR_HISTORY"}[citation["source"]]
                        evidence.append(VerifiedEvidence(Evidence(citation["quote"],source,citation.get("history_index")),"supported",component["reason"]))
        results[code] = GDResult(code,"NA" if decision["status"]=="N/A" else decision["status"],
            decision["score"],decision["reason"],tuple(evidence),rule_version=VERSION)
    return {"results":results,"extraction":extraction,"independent_verification":verification,
            "decisions":decisions,"rule_version":VERSION}
