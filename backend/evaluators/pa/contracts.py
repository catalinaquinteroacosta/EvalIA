from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

Status = Literal['supported','unsupported','ambiguous']
Source = Literal['history','user','response']
CODES = tuple(f'PA{i}' for i in range(1,9))
CONDITIONAL = frozenset({'PA2','PA3','PA8'})

@dataclass(frozen=True)
class Message:
    role: Literal['user','assistant']
    text: str

@dataclass(frozen=True)
class Turn:
    user: str
    response: str
    prior_history: tuple[Message,...] = ()

@dataclass(frozen=True)
class Evidence:
    source: Source
    quote: str
    history_index: int | None = None

@dataclass(frozen=True)
class Finding:
    component: str
    value: bool
    evidence: tuple[Evidence,...] = ()
    explanation: str = ''

@dataclass(frozen=True)
class Verification:
    component: str
    status: Status
    reason: str
    counterevidence: tuple[Evidence,...] = ()

@dataclass(frozen=True)
class Result:
    indicator: str
    score: int | str
    reason: str
    findings: tuple[Finding,...] = ()
    verification: tuple[Verification,...] = ()
