"""
EvalIA - Prompt para relación Activación -> Acción/Interferencia.

Evalúa exclusivamente si una activación ya identificada está
semánticamente relacionada con una interferencia ya identificada.

No descubre hechos nuevos.
No asigna puntuaciones.
No decide aplicabilidad final de AF7.
"""

from __future__ import annotations


def build_activation_action_prompt(
    *,
    context: str,
    activation_description: str,
    activation_evidence: str,
    action_description: str,
    interference_description: str,
    interference_evidence: str,
) -> str:

    return f"""
Eres un validador semántico restringido del framework EvalIA.

Debes determinar exclusivamente si la ACTIVACIÓN identificada está
relacionada con la INTERFERENCIA sobre la ACCIÓN identificada.

No descubras nuevas emociones.
No descubras nuevas acciones.
No asignes puntuaciones.
No decidas AF7.
No completes información ausente.

============================================================
CONTEXTO ORIGINAL
============================================================

{context}

============================================================
ACTIVACIÓN YA IDENTIFICADA
============================================================

Descripción:
{activation_description}

Evidencia literal:
{activation_evidence}

============================================================
ACCIÓN YA IDENTIFICADA
============================================================

{action_description}

============================================================
INTERFERENCIA YA IDENTIFICADA
============================================================

Descripción:
{interference_description}

Evidencia literal:
{interference_evidence}

============================================================
PREGUNTA ÚNICA
============================================================

¿El contexto sustenta que la activación identificada interfiere con
iniciar, sostener, continuar o completar la acción identificada?

Evalúa solamente esa relación.

La mera coexistencia de activación e interferencia NO demuestra relación.

Ejemplo conceptual:

"Estoy nervioso por una discusión con mi pareja y no logro empezar el
informe porque no entiendo las instrucciones."

Puede existir activación y puede existir interferencia con una acción,
pero el texto NO sustenta que el nerviosismo sea responsable de la
interferencia con el informe.

No relaciones hechos solamente porque aparecen en el mismo texto.

============================================================
SUPPORTED
============================================================

Usa "supported" únicamente cuando el texto conecte de manera directa o
semánticamente inequívoca la activación con la dificultad para realizar
la acción.

La conexión puede expresarse mediante:

- causalidad explícita;
- relación temporal-funcional inequívoca;
- descripción en la que la activación obstaculiza claramente la acción.

Ejemplo conceptual:

"Cuando intento empezar el informe me pongo tan nervioso que termino
cerrándolo."

La relación está sustentada.

No es necesario que aparezcan palabras exactas como "causa" o "impide".

============================================================
NOT_SUPPORTED
============================================================

Usa "not_supported" cuando:

- activación e interferencia simplemente coexisten;
- pertenecen a problemas diferentes;
- falta el vínculo entre ambas;
- el contexto aporta una explicación diferente para la interferencia;
- afirmar la relación exige completar información ausente.

Una relación plausible NO equivale a evidencia.

============================================================
AMBIGUOUS
============================================================

Usa "ambiguous" únicamente cuando el propio texto sustente más de una
interpretación razonable sobre la relación y no permita resolver cuál
corresponde.

Debe existir evidencia textual para la ambigüedad.

La simple ausencia de información NO es ambigüedad:
es "not_supported".

La mera posibilidad de imaginar una conexión tampoco es ambigüedad.

============================================================
CONTRAEVIDENCIA
============================================================

Busca también evidencia que debilite o contradiga la relación.

Ejemplo conceptual:

"Me pongo nervioso antes de entrar, pero entro normalmente."

No debe interpretarse como interferencia causada por la activación.

Si existe evidencia explícita de que la acción continúa normalmente,
debe considerarse al decidir el estado.

============================================================
EVIDENCIA
============================================================

supporting_evidence y counterevidence solo pueden contener fragmentos
literales del CONTEXTO ORIGINAL.

No parafrasees dentro de esos campos.
No inventes citas.

Si status = "supported", debe existir evidencia pertinente que sustente
la relación.

Si status = "not_supported" y no existe contraevidencia literal,
counterevidence puede quedar vacío.

Si status = "ambiguous", conserva las citas pertinentes que expliquen
por qué el propio texto permite interpretaciones diferentes.

============================================================
CONTROL FINAL
============================================================

Antes de responder verifica:

1. ¿Estoy evaluando una relación y no simplemente dos hechos?
2. ¿El texto conecta realmente la activación con la acción interferida?
3. ¿Estoy suponiendo causalidad porque ambas aparecen cerca?
4. ¿Existe una explicación alternativa explícita?
5. ¿La ambigüedad está en el texto o solamente en mi imaginación?
6. ¿Todas las citas devueltas existen literalmente en el contexto?

Devuelve exclusivamente el JSON exigido por el schema.
No añadas texto fuera del JSON.
""".strip()