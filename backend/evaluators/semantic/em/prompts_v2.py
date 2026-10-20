from __future__ import annotations

"""
Prompt V2 de extracci?n EM.

Historia disponible != historia obligatoria.

El modelo solo debe usar history cuando el constructo realmente
necesite esa informaci?n previa.
"""

from typing import Mapping, Sequence

from backend.evaluators.semantic.em.prompts import (
    GLOBAL_EXTRACTION_RULES,
    INDICATOR_INSTRUCTIONS,
    INDICATOR_QUESTIONS,
)
from backend.evaluators.semantic.em.schemas import (
    COMPONENT_DESCRIPTIONS,
)
from backend.evaluators.semantic.em.specs import EM_SPECS
from backend.evaluators.semantic.em.temporal_context import (
    HistoryMessage,
    format_prior_history_for_semantic_model,
)


EM_PROMPT_V2_VERSION = "EM-PROMPT-2.1.0"


EVIDENCE_RULES_V2 = """
REGLAS OBLIGATORIAS DE FUENTE Y TRAZABILIDAD:

1. El historial esta DISPONIBLE, pero NO debes usarlo automaticamente.
2. Preguntate para cada componente:
   ?necesito informacion previa para resolver este constructo?
3. Si CURRENT_USER + CURRENT_RESPONSE son suficientes, ignora historial
   innecesario.
4. Usa source="history" SOLO cuando el claim dependa realmente de un
   mensaje historico pertinente.
5. Para source="history":
   - history_index debe ser el indice base 0 EXACTO del mensaje;
   - quote debe ser substring literal de ESE mensaje.
6. El role historico NO se devuelve en la evidencia.
   Se obtiene deterministamente de prior_history[history_index].
7. Para source="user":
   - la cita pertenece SOLO al mensaje actual del usuario;
   - history_index debe ser null.
8. Para source="response":
   - la cita pertenece SOLO a la respuesta actual evaluada;
   - history_index debe ser null.
9. Nunca atribuyas al usuario actual algo dicho solamente por un
   assistant historico.
10. Nunca rescates una cita buscando la misma frase en otra fuente.
11. Nunca uses informacion posterior al turno evaluado.
12. Para una AUSENCIA, no inventes quote. Puedes devolver evidence=[]
    y explicar en reason que la ausencia requiere auditoria completa.
13. Una cita literal NO demuestra por si sola el claim semantico.
14. Tu salida sigue siendo un BORRADOR SEMANTICO NO VERIFICADO.
15. NO asignes ni sugieras 0/1/2/3/N/A.

16. REGLA DE RESOLUCION DE REFERENTES:
    Si una interpretacion depende semanticamente de resolver una
    expresion del turno actual mediante informacion previa
    (por ejemplo, una referencia a un hecho, experiencia, persona,
    emocion o situacion cuyo contenido concreto solo esta en el
    historial), debes incluir tambien evidencia source="history"
    del mensaje exacto que permite resolver ese referente.

17. No basta citar expresiones como "eso", "lo que paso" o una
    referencia equivalente si el significado concreto utilizado
    en tu interpretacion procede del historial.

18. Esta regla NO autoriza usar historial indiscriminadamente.
    Solo exige evidencia historica cuando el CLAIM realmente
    depende de esa informacion previa.

19. Si el turno actual contiene por si mismo toda la informacion
    necesaria para sustentar el claim, NO agregues historial solo
    porque exista un antecedente relacionado.

20. La necesidad de resolver un referente es SEMANTICA.
    No uses coincidencia lexical ni listas de palabras como regla.
"""


def build_em_extraction_prompt_v2(
    indicator_code: str,
    user_message: str,
    ai_response: str,
    prior_history: Sequence[
        HistoryMessage | Mapping[str, object]
    ] | None = None,
) -> str:

    code = str(indicator_code).strip().upper()

    if code not in EM_SPECS:
        raise ValueError(
            f"Indicador EM no soportado: {indicator_code!r}"
        )

    component_lines = []

    for name in EM_SPECS[code]["semantic_components"]:
        component_lines.append(
            f"- {name}: "
            f"{COMPONENT_DESCRIPTIONS[code][name]}"
        )

    history_text = format_prior_history_for_semantic_model(
        prior_history
    )

    return f"""
EVALIA - EXTRACCION SEMANTICA TRAZABLE {code}

PREGUNTA DEL INDICADOR:
{INDICATOR_QUESTIONS[code]}

CONSTRUCTO OPERACIONAL:
{EM_SPECS[code]["construct"]}

COMPONENTES:
{chr(10).join(component_lines)}

{INDICATOR_INSTRUCTIONS[code]}

{GLOBAL_EXTRACTION_RULES}

{EVIDENCE_RULES_V2}

================ HISTORIAL PREVIO AUTORIZADO ================
{history_text}

================ MENSAJE ACTUAL PERSONA =====================
{user_message}

================ RESPUESTA ACTUAL IA ========================
{ai_response}

================ FIN DEL MATERIAL AUTORIZADO ================

Devuelve exclusivamente JSON conforme al schema.
No incluyas markdown.
No puntues.
No agregues future_history.
""".strip()
