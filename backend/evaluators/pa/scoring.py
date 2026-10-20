"""Fail-closed scoring; semantic judgments must be independently verified.
A level claim is a validated *semantic* assessment, never an LLM-produced score.
"""
from dataclasses import dataclass
from .contracts import Result, Finding, Verification, CONDITIONAL, CODES
from .rubric import ANCHORS

@dataclass(frozen=True)
class Assessment:
    applicable: bool | None
    # Independently verified rubric-level properties, not a numerical score.
    behavior_present: bool | None
    central_function_met: bool | None
    contextual_complete: bool | None
    secondary_defect: bool | None
    material_contradiction: bool | None
    reason: str

def decide(code: str, assessment: Assessment, findings: tuple[Finding,...]=(), verification: tuple[Verification,...]=()) -> Result:
    if code not in CODES: raise ValueError(code)
    if not assessment.reason.strip():
        return Result(code,'BLOCKED','Missing audit rationale',findings,verification)
    if not verification or any(v.status != 'supported' for v in verification):
        return Result(code,'BLOCKED','Unresolved independent verification',findings,verification)

    verified_components = [v.component for v in verification]
    if len(verified_components) != len(set(verified_components)):
        return Result(code,'BLOCKED','Duplicate component verification',findings,verification)

    if assessment.applicable is False:
        if verified_components != ['applicability']:
            return Result(code,'BLOCKED','Applicability not independently verified',findings,verification)
    else:
        required = {'applicability'} | {f.component for f in findings}
        if not required.issubset(set(verified_components)):
            return Result(code,'BLOCKED','Incomplete component verification',findings,verification)

    if assessment.applicable is None:
        return Result(code,'BLOCKED','Applicability unresolved',findings,verification)
    if not assessment.applicable:
        if code not in CONDITIONAL:
            return Result(
                code,
                'BLOCKED',
                'N/A no permitido para indicador general',
                findings,
                verification,
            )
        return Result(
            code, 'N/A', assessment.reason,
            findings, verification
        )
    a=assessment
    if any(getattr(a,k) is None for k in ('behavior_present','central_function_met','contextual_complete','secondary_defect','material_contradiction')):
        return Result(code,'BLOCKED','Incomplete semantic assessment',findings,verification)
    if a.material_contradiction or not a.behavior_present: level=0
    elif not a.central_function_met: level=1
    elif a.contextual_complete and not a.secondary_defect: level=3
    else: level=2
    return Result(code,level,assessment.reason+' | '+ANCHORS[level],findings,verification)
