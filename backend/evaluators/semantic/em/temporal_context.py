from __future__ import annotations

"""
Contrato temporal privado de EM.

Reglas:
- prior_history contiene mensajes INDIVIDUALES y ordenados.
- cada mensaje tiene exactamente role + text.
- no existe future_history.
- history_index es base 0.
- disponibilidad del historial NO implica obligacion de usarlo.
"""

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence


EM_TEMPORAL_CONTEXT_VERSION = "EM-TEMPORAL-CONTEXT-1.0.0"

VALID_HISTORY_ROLES = frozenset({"user", "assistant"})


@dataclass(frozen=True)
class HistoryMessage:
    role: str
    text: str


def normalize_prior_history(
    prior_history: Sequence[HistoryMessage | Mapping[str, object]] | None,
) -> tuple[HistoryMessage, ...]:
    """
    Convierte historial autorizado a una representacion inmutable.

    No concatena mensajes.
    No acepta roles distintos de user/assistant.
    No admite campos temporales futuros.
    """
    if prior_history is None:
        return ()

    if isinstance(prior_history, (str, bytes)):
        raise TypeError(
            "prior_history debe ser una secuencia de mensajes individuales, "
            "no un bloque de texto"
        )

    normalized: list[HistoryMessage] = []

    for index, item in enumerate(prior_history):
        if isinstance(item, HistoryMessage):
            role = item.role
            text = item.text

        elif isinstance(item, Mapping):
            keys = set(item)

            if keys != {"role", "text"}:
                raise ValueError(
                    f"prior_history[{index}] debe contener exactamente "
                    f"role y text; recibido={sorted(keys)!r}"
                )

            role = item["role"]
            text = item["text"]

        else:
            raise TypeError(
                f"prior_history[{index}] debe ser HistoryMessage o mapping"
            )

        if not isinstance(role, str) or role not in VALID_HISTORY_ROLES:
            raise ValueError(
                f"Rol historico invalido en indice {index}: {role!r}"
            )

        if not isinstance(text, str):
            raise TypeError(
                f"Texto historico invalido en indice {index}: "
                f"debe ser str"
            )

        normalized.append(
            HistoryMessage(
                role=role,
                text=text,
            )
        )

    return tuple(normalized)


def get_history_message(
    prior_history: Sequence[HistoryMessage | Mapping[str, object]] | None,
    history_index: int,
) -> HistoryMessage:
    history = normalize_prior_history(prior_history)

    if isinstance(history_index, bool) or not isinstance(history_index, int):
        raise TypeError("history_index debe ser int base 0")

    if history_index < 0 or history_index >= len(history):
        raise IndexError(
            f"history_index fuera de rango: {history_index}"
        )

    return history[history_index]


def history_role_at(
    prior_history: Sequence[HistoryMessage | Mapping[str, object]] | None,
    history_index: int,
) -> str:
    """
    El rol se deriva del mensaje historico.
    Nunca se almacena redundantemente en la evidencia.
    """
    return get_history_message(
        prior_history,
        history_index,
    ).role


def format_prior_history_for_semantic_model(
    prior_history: Sequence[HistoryMessage | Mapping[str, object]] | None,
) -> str:
    """
    Serializacion explicita para prompts.

    Conserva indice y rol por mensaje.
    No convierte el historial en evidencia automaticamente.
    """
    history = normalize_prior_history(prior_history)

    if not history:
        return "[SIN HISTORIAL PREVIO]"

    blocks: list[str] = []

    for index, message in enumerate(history):
        blocks.append(
            "\n".join(
                (
                    f"[history_index={index}]",
                    f"role={message.role}",
                    "text:",
                    message.text,
                )
            )
        )

    return "\n\n".join(blocks)
