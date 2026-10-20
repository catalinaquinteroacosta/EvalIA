
from dataclasses import dataclass
from typing import Literal

Truth = Literal["true", "false", "uncertain"]
Verdict = Literal[
    "supported", "not_supported", "ambiguous"
]

@dataclass(frozen=True)
class AtomicFinding:
    code: str
    claim_id: str
    proposition: str
    truth: Truth
    evidence: tuple

@dataclass(frozen=True)
class IndependentCheck:
    code: str
    claim_id: str
    verified_truth: Truth
    verdict: Verdict

def reconcile(
    finding: AtomicFinding,
    check: IndependentCheck,
) -> str:
    if finding.code != check.code:
        raise ValueError("Codigo de indicador distinto")

    if finding.claim_id != check.claim_id:
        raise ValueError("Identificador de afirmacion distinto")

    if finding.truth == "uncertain":
        return "BLOCKED"

    if check.verified_truth == "uncertain":
        return "BLOCKED"

    if check.verdict == "ambiguous":
        return "BLOCKED"

    agreement = (
        finding.truth == check.verified_truth
    )

    if agreement and check.verdict == "supported":
        return "VERIFIED"

    if not agreement and check.verdict == "not_supported":
        return "DISAGREEMENT"

    return "INCONSISTENT"
