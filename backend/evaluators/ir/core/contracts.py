"""Contratos privados de IR. No asignan puntuaciones."""

from dataclasses import dataclass
from typing import Literal, Optional, Tuple

Source = Literal["history", "user", "response"]
Role = Literal["user", "assistant"]
Verification = Literal[
    "supported", "unsupported", "ambiguous"
]


@dataclass(frozen=True)
class Message:
    role: Role
    text: str

    def __post_init__(self):
        if self.role not in ("user", "assistant"):
            raise ValueError("Rol histórico inválido")
        if not isinstance(self.text, str):
            raise TypeError("Texto histórico inválido")


@dataclass(frozen=True)
class Context:
    user: str
    response: str
    prior_history: Tuple[Message, ...] = ()

    def __post_init__(self):
        if not isinstance(self.user, str):
            raise TypeError("Usuario inválido")
        if not isinstance(self.response, str):
            raise TypeError("Respuesta inválida")
        if not isinstance(self.prior_history, tuple):
            raise TypeError("Historial debe ser tupla")
        if not all(
            isinstance(m, Message) for m in self.prior_history
        ):
            raise TypeError("Historial contiene mensajes inválidos")


@dataclass(frozen=True)
class Evidence:
    source: Source
    quote: str
    history_index: Optional[int] = None

    def __post_init__(self):
        if self.source not in ("history", "user", "response"):
            raise ValueError("Fuente inválida")
        if not isinstance(self.quote, str) or not self.quote:
            raise ValueError("Cita vacía o inválida")
        if self.source == "history":
            if type(self.history_index) is not int:
                raise ValueError("Índice histórico obligatorio")
            if self.history_index < 0:
                raise ValueError("Índice histórico negativo")
        elif self.history_index is not None:
            raise ValueError("Índice prohibido para fuente actual")