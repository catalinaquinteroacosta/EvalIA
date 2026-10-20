"""Reparaci?n controlada de citas literales CE-A."""

import json

from backend.evaluators.semantic.semantic_provider import (
    run_structured_semantic,
)

from .extractor import SCHEMA, validate_extraction


class CEACitationRepairError(ValueError):
    pass


def repair_citations(
    extraction,
    *,
    user_text,
    response_text,
    prior_context="",
    model,
):
    """
    Un ?nico intento de reparaci?n.
    Nunca elimina validaciones ni asigna puntuaciones.
    """

    prompt = """
Repara exclusivamente los errores de citas literales
del siguiente JSON de extracci?n CE-A.

REGLAS OBLIGATORIAS:

1. Cada evidencia debe ser una subcadena literal,
   continua y exacta del texto de origen.

2. No utilices puntos suspensivos para unir
   fragmentos separados.

3. No inventes ni reformules el texto de las citas.

4. Conserva las interpretaciones que est?n
   correctamente respaldadas.

5. Si una interpretaci?n no tiene respaldo,
   elimina ese elemento de su lista.

6. No a?adas interpretaciones nuevas.

7. Para necesidades y omisiones, respeta
   estrictamente su campo source.

8. No modifiques la estructura del esquema.
   No asignes puntuaciones.

MENSAJE ACTUAL:
""" + json.dumps(user_text, ensure_ascii=False) + """

CONTEXTO PREVIO:
""" + json.dumps(prior_context, ensure_ascii=False) + """

RESPUESTA:
""" + json.dumps(response_text, ensure_ascii=False) + """

EXTRACCI?N A REPARAR:
""" + json.dumps(extraction, ensure_ascii=False)

    repaired = run_structured_semantic(
        prompt=prompt,
        schema=SCHEMA,
        provider="openai",
        model=model,
        max_output_tokens=4096,
    )

    try:
        return validate_extraction(
            repaired,
            response_text,
            user_text,
            prior_context,
        )
    except ValueError as exc:
        raise CEACitationRepairError(
            "La reparaci?n no super? la validaci?n literal."
        ) from exc
