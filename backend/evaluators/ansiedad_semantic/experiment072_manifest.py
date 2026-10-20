"""Build an unevaluated 072 manifest; never treat historical scores as truth."""
from pathlib import Path
from hashlib import sha256
import json
from backend.evaluators.ansiedad_semantic.official_contracts import EXPECTED

def build(root):
    root=Path(root)
    a=root/"backend/evaluators/semantic/em/reports/experiment72_dataset.json"
    b=root/"backend/evaluators/ir/fixtures/independent/ir_exp072_25_cases.json"
    rows=json.loads(a.read_text(encoding="utf-8-sig"))
    ir=json.loads(b.read_text(encoding="utf-8-sig"))["cases"]
    index={(r["model"],r["turn"]):r for r in rows}
    other={(r["model"],r["turn"]):r for r in ir}
    if len(index)!=25 or set(index)!=set(other):raise ValueError("Corpus identity mismatch")
    errors=[]; tasks=[]
    for (model,turn),r in index.items():
        if r["user_message"]!=other[model,turn]["user"] or r["ai_response"]!=other[model,turn]["response"]:errors.append([model,turn,"text mismatch"])
        expected=[]
        for earlier in range(1,turn):
            prev=index[model,earlier]
            expected.extend([{"role":"user","text":prev["user_message"]},{"role":"assistant","text":prev["ai_response"]}])
        if r["prior_history"]!=expected or other[model,turn]["prior_history"]!=expected:errors.append([model,turn,"history mismatch"])
        identity=sha256(json.dumps(r,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        for family,count in EXPECTED.items():
            for n in range(1,count+1):
                tasks.append({"model":model,"turn":turn,"indicator":f"{family}{n}","input_sha256":identity,"status":"PENDING","score":None,"applicability":"NOT_YET_VERIFIED"})
    return {"experiment":72,"source_hashes":{str(p.relative_to(root)):sha256(p.read_bytes()).hexdigest() for p in (a,b)},"responses":len(rows),"models":sorted({m for m,t in index}),"tasks":tasks,"history_errors":errors,"evaluations_executed":0,"api_calls":0,"clinical_validation":False}
