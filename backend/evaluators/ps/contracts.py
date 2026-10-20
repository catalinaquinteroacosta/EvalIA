from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

Source = Literal['history', 'user', 'response']
Verification = Literal['supported', 'unsupported', 'ambiguous']

@dataclass(frozen=True)
class HistoryMessage:
    role: Literal['user', 'assistant']
    text: str

@dataclass(frozen=True)
class Turn:
    user: str
    response: str
    prior_history: tuple[HistoryMessage, ...] = ()

@dataclass(frozen=True)
class Evidence:
    source: Source
    quote: str
    history_index: int | None = None

@dataclass(frozen=True)
class Claim:
    indicator: str
    predicate: str
    evidence: tuple[Evidence, ...]
    verification: Verification | None = None
    counterevidence: tuple[Evidence, ...] = ()

@dataclass(frozen=True)
class Decision:
    indicator: str
    score: int | None
    status: Literal['SCORED','NA','BLOCKED','MISSING_DATA']
    reason: str
