from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ConversationTurn:
    """
    Representa un turno completo de la conversación.

    Incluye el mensaje de la persona y la respuesta producida
    por el modelo evaluado.
    """

    turn_number: int
    user_message: str
    ai_response: str

    def __post_init__(self) -> None:
        if self.turn_number <= 0:
            raise ValueError(
                "El número del turno debe ser mayor que cero."
            )

        if not self.user_message.strip():
            raise ValueError(
                "El mensaje del usuario no puede estar vacío."
            )

        if not self.ai_response.strip():
            raise ValueError(
                "La respuesta de la IA no puede estar vacía."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_number": self.turn_number,
            "user_message": self.user_message.strip(),
            "ai_response": self.ai_response.strip(),
        }


@dataclass
class EvaluationContext:
    """
    Contexto completo utilizado por el motor automático de EvalIA.

    Permite evaluar un turno individual sin perder el historial
    de la conversación ni la información general del experimento.
    """

    experiment_id: int
    scenario_code: str
    rubric_type: str
    model_name: str
    turns: list[ConversationTurn]

    scenario_title: str = ""
    scenario_category: str = ""
    scenario_description: str = ""

    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.scenario_code = self.scenario_code.strip()
        self.rubric_type = self.rubric_type.strip().lower()
        self.model_name = self.model_name.strip()

        self.scenario_title = self.scenario_title.strip()
        self.scenario_category = self.scenario_category.strip()
        self.scenario_description = (
            self.scenario_description.strip()
        )

        if self.experiment_id <= 0:
            raise ValueError(
                "El identificador del experimento debe ser mayor que cero."
            )

        if not self.scenario_code:
            raise ValueError(
                "El código del escenario no puede estar vacío."
            )

        if not self.rubric_type:
            raise ValueError(
                "El tipo de rúbrica no puede estar vacío."
            )

        if not self.model_name:
            raise ValueError(
                "El nombre del modelo no puede estar vacío."
            )

        if not self.turns:
            raise ValueError(
                "La evaluación requiere al menos un turno."
            )

        turn_numbers = [
            turn.turn_number
            for turn in self.turns
        ]

        if len(turn_numbers) != len(set(turn_numbers)):
            raise ValueError(
                "La conversación contiene números de turno duplicados."
            )

        self.turns.sort(
            key=lambda turn: turn.turn_number
        )

    @property
    def total_turns(self) -> int:
        return len(self.turns)

    @property
    def complete_user_text(self) -> str:
        """
        Une todos los mensajes de la persona para análisis global.
        """
        return "\n\n".join(
            turn.user_message.strip()
            for turn in self.turns
        )

    @property
    def complete_ai_text(self) -> str:
        """
        Une todas las respuestas del modelo para análisis global.
        """
        return "\n\n".join(
            turn.ai_response.strip()
            for turn in self.turns
        )

    @property
    def complete_conversation_text(self) -> str:
        """
        Construye una representación legible de toda la conversación.
        """
        blocks: list[str] = []

        for turn in self.turns:
            blocks.append(
                (
                    f"TURNO {turn.turn_number}\n"
                    f"USUARIO:\n{turn.user_message.strip()}\n\n"
                    f"IA:\n{turn.ai_response.strip()}"
                )
            )

        return "\n\n---\n\n".join(blocks)

    def get_turn(
        self,
        turn_number: int,
    ) -> ConversationTurn:
        """
        Obtiene un turno por su número.
        """
        for turn in self.turns:
            if turn.turn_number == turn_number:
                return turn

        raise ValueError(
            f"No existe el turno {turn_number}."
        )

    def get_previous_turns(
        self,
        turn_number: int,
    ) -> list[ConversationTurn]:
        """
        Devuelve todos los turnos anteriores al indicado.
        """
        return [
            turn
            for turn in self.turns
            if turn.turn_number < turn_number
        ]

    def get_turns_until(
        self,
        turn_number: int,
    ) -> list[ConversationTurn]:
        """
        Devuelve el historial disponible hasta el turno indicado,
        incluyendo el turno actual.
        """
        return [
            turn
            for turn in self.turns
            if turn.turn_number <= turn_number
        ]

    def get_ai_responses_until(
        self,
        turn_number: int,
    ) -> str:
        """
        Une las respuestas de la IA disponibles hasta el turno actual.
        """
        return "\n\n".join(
            turn.ai_response.strip()
            for turn in self.get_turns_until(turn_number)
        )

    def get_user_messages_until(
        self,
        turn_number: int,
    ) -> str:
        """
        Une los mensajes de la persona disponibles hasta el turno actual.
        """
        return "\n\n".join(
            turn.user_message.strip()
            for turn in self.get_turns_until(turn_number)
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convierte el contexto en una estructura serializable.
        """
        return {
            "experiment_id": self.experiment_id,
            "scenario_code": self.scenario_code,
            "scenario_title": self.scenario_title,
            "scenario_category": self.scenario_category,
            "scenario_description": self.scenario_description,
            "rubric_type": self.rubric_type,
            "model_name": self.model_name,
            "total_turns": self.total_turns,
            "turns": [
                turn.to_dict()
                for turn in self.turns
            ],
            "metadata": self.metadata,
        }