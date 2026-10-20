"""Immutable temporal input and documentary contracts. Standard library only."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / "docs" / "crisis_semantic"
PRIVATE = Path(__file__).resolve().parent / "private_pilot"
PACKAGES = {"P1": ("RI", "NI"), "P2": ("CS", "CT"), "P3": ("PP", "AC", "RE"), "P4": ("OP", "CE", "GA")}

def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

@dataclass(frozen=True)
class Turn:
    number: int
    user: str
    ai: str
    model: str

@dataclass(frozen=True)
class Input:
    current: Turn
    history: tuple[Turn, ...] = ()

    def __post_init__(self):
        if type(self.current.number) is not int or self.current.number < 1:
            raise ValueError("invalid_turn_number")
        if not isinstance(self.current.user, str) or not isinstance(self.current.ai, str) or not self.current.model:
            raise ValueError("invalid_turn_fields")
        numbers = [t.number for t in self.history]
        if numbers != sorted(numbers) or len(set(numbers)) != len(numbers):
            raise ValueError("history_not_ordered_unique")
        if any(t.number >= self.current.number or t.model != self.current.model for t in self.history):
            raise ValueError("future_or_other_model_history")

    @classmethod
    def from_conversation(cls, turns, number, model):
        selected = [t for t in turns if t.number == number and t.model == model]
        if len(selected) != 1:
            raise ValueError("current_turn_not_unique")
        prior = tuple(sorted((t for t in turns if t.number < number and t.model == model), key=lambda t: t.number))
        return cls(selected[0], prior)

    def payload(self):
        return {"current_user": self.current.user, "current_ai": self.current.ai,
                "current_turn": self.current.number, "model_evaluated": self.current.model,
                "history": [{"index": n, **asdict(t)} for n, t in enumerate(self.history)]}

    def text(self, source, index):
        if source in ("current_user", "current_ai"):
            if index is not None:
                raise ValueError("unexpected_history_index")
            return self.current.user if source == "current_user" else self.current.ai
        if source not in ("prior_user", "prior_ai") or type(index) is not int or not 0 <= index < len(self.history):
            raise ValueError("invalid_history_source_or_index")
        turn = self.history[index]
        return turn.user if source == "prior_user" else turn.ai

def load_contracts():
    manifest = json.loads((DOCS / "manifest.json").read_text(encoding="utf-8"))
    artifacts = {item["file"]: item["sha256"] for item in manifest["generated_artifacts"]}
    contracts = {}
    for family in manifest["families"]:
        path = DOCS / family["file"]
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != artifacts[path.name]:
            raise ValueError("document_contract_hash_mismatch")
        data = json.loads(raw)
        if data["source_sha256"] != manifest["source_sha256"]:
            raise ValueError("document_source_identity_mismatch")
        for item in data["indicators"]:
            if item["code"] in contracts:
                raise ValueError("duplicate_contract")
            contracts[item["code"]] = item
    common_bytes = (DOCS / "common_rules.json").read_bytes()
    if hashlib.sha256(common_bytes).hexdigest() != artifacts["common_rules.json"]:
        raise ValueError("common_rules_hash_mismatch")
    if len(contracts) != 104:
        raise ValueError("incomplete_contract_inventory")
    return contracts, manifest, json.loads(common_bytes)

def package_codes(contracts, package):
    return [code for code in contracts if code.split("-")[1].rstrip("0123456789") in PACKAGES[package]]
