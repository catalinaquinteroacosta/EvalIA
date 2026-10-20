"""EvalIA CP — contexto temporal de evaluación.

Regla fundamental:

Para evaluar el turno actual solo puede utilizarse información
disponible hasta ese turno:

    historial previo
    + mensaje actual del usuario
    + respuesta actual evaluada

Nunca se permiten turnos posteriores.

Este módulo NO:
- interpreta semánticamente;
- decide aplicabilidad;
- asigna puntuaciones;
- modifica la rúbrica.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ConversationRole = Literal[
    "user",
    "assistant",
]


@dataclass(frozen=True)
class PriorTurn:
    """Mensaje perteneciente exclusivamente al historial previo."""

    role: ConversationRole
    text: str

    def __post_init__(self) -> None:
        if not isinstance(self.text, str):
            raise TypeError(
                "PriorTurn.text debe ser str."
            )

        if not self.text.strip():
            raise ValueError(
                "PriorTurn.text no puede estar vacío."
            )


@dataclass(frozen=True)
class CPEvaluationContext:
    """Ventana causal disponible al evaluar una respuesta.

    prior_history:
        Solo mensajes anteriores al mensaje actual.

    current_user_message:
        Mensaje del usuario correspondiente al turno evaluado.

    current_response:
        Respuesta de IA que está siendo evaluada.

    La clase no admite ni representa future_history
    deliberadamente.
    """

    prior_history: tuple[PriorTurn, ...]
    current_user_message: str
    current_response: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.prior_history,
            tuple,
        ):
            raise TypeError(
                "prior_history debe ser tuple."
            )

        if not isinstance(
            self.current_user_message,
            str,
        ):
            raise TypeError(
                "current_user_message debe ser str."
            )

        if not isinstance(
            self.current_response,
            str,
        ):
            raise TypeError(
                "current_response debe ser str."
            )

        if not self.current_user_message.strip():
            raise ValueError(
                "current_user_message no puede estar vacío."
            )

        if not self.current_response.strip():
            raise ValueError(
                "current_response no puede estar vacío."
            )

    @property
    def prior_user_messages(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            turn.text
            for turn in self.prior_history
            if turn.role == "user"
        )

    @property
    def prior_assistant_messages(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            turn.text
            for turn in self.prior_history
            if turn.role == "assistant"
        )

    def source_texts(
        self,
        source: str,
    ) -> tuple[str, ...]:
        """Devuelve textos autorizados para evidencia literal."""

        if source == "history":
            return tuple(
                turn.text
                for turn in self.prior_history
            )

        if source == "user":
            return (
                self.current_user_message,
            )

        if source == "response":
            return (
                self.current_response,
            )

        raise ValueError(
            f"Fuente CP desconocida: {source!r}"
        )
