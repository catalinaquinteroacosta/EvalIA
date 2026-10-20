"""Build authorized history from identified originals, never caller history."""
from dataclasses import dataclass
from hashlib import sha256
import json

@dataclass(frozen=True)
class OriginalTurn:
    conversation: str
    model: str
    turn: int
    user: str
    response: str

    def __post_init__(self):
        if any(not isinstance(value, str) or not value.strip()
               for value in (self.conversation, self.model, self.user, self.response)):
            raise ValueError("Identidad y originales completos requeridos")
        if type(self.turn) is not int or self.turn < 1:
            raise ValueError("Turno positivo requerido")

def authorized_context(originals, conversation, model, turn):
    """Reject duplicate identities and gaps; select strictly earlier own turns."""
    rows = tuple(originals)
    identities = [(r.conversation, r.model, r.turn) for r in rows]
    if len(identities) != len(set(identities)):
        raise ValueError("Original duplicado: identidad no adjudicable")
    selected = {r.turn: r for r in rows if r.conversation == conversation and r.model == model and r.turn <= turn}
    if set(selected) != set(range(1, turn + 1)):
        raise ValueError("Falta turno actual o contexto previo del mismo modelo")
    current = selected[turn]
    history = []
    for earlier in range(1, turn):
        row = selected[earlier]
        history.extend([{"role": "user", "text": row.user},
                        {"role": "assistant", "text": row.response}])
    payload = {"conversation": conversation, "model": model, "turn": turn,
               "user": current.user, "response": current.response, "prior_history": history}
    payload["input_sha256"] = sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return payload
