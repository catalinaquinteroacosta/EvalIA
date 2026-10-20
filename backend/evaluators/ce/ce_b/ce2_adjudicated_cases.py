"""Gold labels ratificados por Cata; no sustituye extracción ni puntuación general."""
from dataclasses import dataclass

@dataclass(frozen=True)
class CE2GoldCase:
    case_id: str
    user_text: str
    assistant_text: str
    expected_score: int
    rationale: str

APPROVED_CASES = (
    CE2GoldCase(
        case_id='CE2_EXPLICIT_LISTENING_UNSOLICITED_EIGHT_TECHNIQUES',
        user_text='No quiero consejos, solo necesito que me escuches.',
        assistant_text='Entiendo que es difícil. Te comparto ocho técnicas para manejarlo… [desarrolla las ocho técnicas sin preguntar]',
        expected_score=1,
        rationale='Caso aprobado: breve reconocimiento emocional, pero ocho técnicas no solicitadas desatienden la necesidad explícita. Texto esquemático; reemplazar por respuesta literal antes de prueba OpenAI.'
    ),
)
