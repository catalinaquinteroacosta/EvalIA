"""Read-only PS preflight. Does not invoke OpenAI or alter any other evaluator."""
from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from .rubric import rubric_for
from .scoring import CODES
from .semantic import EXTRACT_SYSTEM, VERIFY_SYSTEM

@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    detail: str

def audit() -> dict:
    findings=[]
    for code in CODES:
        r=rubric_for(code)
        if not r.get('question') or not r.get('applicability'):
            findings.append(Finding(code,'ERROR','Question/applicability absent'))
        if set(map(str,r.get('reference_levels',{}))) != {'0','1','2','3'}:
            findings.append(Finding(code,'ERROR','Four official anchors missing'))
    if 'never' not in EXTRACT_SYSTEM.lower() and 'not a grader' not in EXTRACT_SYSTEM.lower():
        findings.append(Finding('ALL','ERROR','Extractor grading prohibition missing'))
    if 'urgent' not in VERIFY_SYSTEM.lower() or 'imminent' not in VERIFY_SYSTEM.lower():
        findings.append(Finding('PS3','ERROR','Urgency distinction absent from verifier'))
    # Important methodological warnings, not claims of validated failures.
    findings.extend([
        Finding('ALL','REVIEW','Current verifier chooses which level is supported; independent evidence and rubric fidelity require real-case audit.'),
        Finding('ALL','REVIEW','Positive-level decisions may lack literal response evidence; run semantic pilot and check false positives.'),
        Finding('ALL','REVIEW','Existing unit tests use synthetic verifiers; they do not prove clinical-safety or semantic correctness.'),
        Finding('ALL','REVIEW','Do not assume old regex scores or evaluator targets are ground truth.'),
    ])
    return {'family':'PS','indicators':list(CODES),'error_count':sum(x.severity=='ERROR' for x in findings),
            'review_count':sum(x.severity=='REVIEW' for x in findings),
            'findings':[asdict(x) for x in findings], 'api_calls':0}

def main():
    print(json.dumps(audit(),ensure_ascii=False,indent=2))
    if audit()['error_count']:
        raise SystemExit(1)

if __name__=='__main__':
    main()
