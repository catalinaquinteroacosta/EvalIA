"""No network calls here. Provider adapters are explicit and independently injectable."""
from __future__ import annotations
from typing import Protocol
from .contracts import Turn, Finding, Verification, Result, CODES
from .evidence import validate_evidence
from .scoring import Assessment, decide

class Extractor(Protocol):
    def extract(self, turn: Turn, code: str) -> tuple[Finding,...]: ...
class Verifier(Protocol):
    def verify(self, turn: Turn, code: str, findings: tuple[Finding,...]) -> tuple[Verification,...]: ...
class Assessor(Protocol):
    def assess(self, turn: Turn, code: str, findings: tuple[Finding,...], verifications: tuple[Verification,...]) -> Assessment: ...

def evaluate(turn: Turn, extractor: Extractor, verifier: Verifier, assessor: Assessor) -> dict[str,Result]:
    if not turn.user.strip() or not turn.response.strip():
        raise ValueError('Missing user or response: record as missing data outside ordinal scale')
    out={}
    for code in CODES:
        try:
            findings=extractor.extract(turn,code)
            for f in findings: validate_evidence(turn,f.evidence)
            checks=verifier.verify(turn,code,findings)
            for c in checks: validate_evidence(turn,c.counterevidence)
            # The assessor must be independent of extraction, not a second score generator.
            assessment=assessor.assess(turn,code,findings,checks)
            out[code]=decide(code,assessment,findings,checks)
        except Exception as exc:
            out[code]=Result(code,'BLOCKED',f'{type(exc).__name__}: {exc}')
    return out
