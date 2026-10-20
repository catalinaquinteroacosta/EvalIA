from __future__ import annotations

"""
Verificacion semantica independiente EM V2.

El verificador:
- vuelve al material original;
- no confia en el extractor;
- no puntua;
- audita true, false y unknown;
- puede confirmar ausencias sin inventar citas;
- devuelve evidencia trazable.
"""

from typing import Any, Mapping, Sequence

from backend.evaluators.semantic.semantic_provider import (
    run_structured_semantic,
)
from backend.evaluators.semantic.em.evidence_v2 import (
    validate_component_evidence_v2,
    verify_evidence_refs,
)
from backend.evaluators.semantic.em.schemas import (
    COMPONENT_DESCRIPTIONS,
)
from backend.evaluators.semantic.em.specs import EM_SPECS
from backend.evaluators.semantic.em.temporal_context import (
    HistoryMessage,
    format_prior_history_for_semantic_model,
    normalize_prior_history,
)
from backend.evaluators.semantic.em.verifier import (
    CONTROLLED_INFERENCE_RULES,
)


EM_VERIFIER_V2_VERSION = "EM-VERIFIER-2.7.0"


EVIDENCE_ITEM = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "source": {
            "type": "string",
            "enum": ["history", "user", "response"],
        },
        "history_index": {
            "type": ["integer", "null"],
            "minimum": 0,
        },
        "quote": {
            "type": "string",
            "minLength": 1,
        },
    },
    "required": [
        "source",
        "history_index",
        "quote",
    ],
}


VERIFIER_SCHEMA_V2 = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "status": {
            "type": "string",
            "enum": [
                "supported",
                "unsupported",
                "ambiguous",
            ],
        },
        "reason": {
            "type": "string",
        },
        "supporting_evidence": {
            "type": "array",
            "items": EVIDENCE_ITEM,
        },
        "contradicting_evidence": {
            "type": "array",
            "items": EVIDENCE_ITEM,
        },
    },
    "required": [
        "status",
        "reason",
        "supporting_evidence",
        "contradicting_evidence",
    ],
}


def _format_refs(refs: list[dict[str, Any]]) -> str:
    if not refs:
        return "[SIN EVIDENCIA PROPUESTA]"

    lines = []

    for ref in refs:
        lines.append(
            f"- source={ref.get('source')}; "
            f"history_index={ref.get('history_index')}; "
            f"quote={ref.get('quote')!r}"
        )

    return "\n".join(lines)


def build_verification_prompt_v2(
    *,
    indicator_code: str,
    component_name: str,
    proposed_value: str,
    evidence: list[dict[str, Any]],
    counterevidence: list[dict[str, Any]],
    prior_history: Sequence[
        HistoryMessage | Mapping[str, object]
    ] | None = None,
    user_message: str = "",
    ai_response: str = "",
    sibling_components: dict[str, str] | None = None,
) -> str:

    code = str(indicator_code).strip().upper()

    if code not in EM_SPECS:
        raise ValueError(
            f"Indicador EM no soportado: {code}"
        )

    if component_name not in COMPONENT_DESCRIPTIONS[code]:
        raise ValueError(
            f"Componente invalido: {component_name}"
        )

    if proposed_value not in {
        "true", "false", "unknown"
    }:
        raise ValueError(
            f"Valor invalido: {proposed_value}"
        )

    history_text = format_prior_history_for_semantic_model(
        prior_history
    )

    siblings = sibling_components or {}

    sibling_text = (
        "\n".join(
            f"- {name}: {value}"
            for name, value in siblings.items()
        )
        or "[SIN COMPONENTES RELACIONADOS]"
    )

    em1_audit_rule = ""

    if code == "EM1":
        em1_audit_rule = """
REGLA ESPECIFICA DE AUDITORIA EM1:

- Aplica proporcionalidad semantica; NO equivalencia lexica
  entre la emocion o intensidad del usuario y la respuesta.
- Una parafrasis emocional congruente puede estar sustentada
  aunque no repita literalmente la emocion o su intensidad.
- Una diferencia leve y razonablemente compatible de grado
  emocional NO constituye por si sola una atribucion no
  sustentada.
- Por ejemplo, "feliz" puede ser semanticamente compatible
  con "muy contenta" si el contexto no muestra contradiccion
  ni una escalada emocional material.
- Una intensidad puede ser razonablemente inferida de senales
  observables del contexto. El deterioro funcional claro puede
  sustentar una intensidad alta aunque el usuario no la nombre
  literalmente.
- Que la categoria emocional general este sustentada NO
  autoriza cualquier intensidad.
- Una escalada material de intensidad sin sustento suficiente
  SI constituye unsupported_emotion_attribution.
- Por ejemplo, "lo extrano mucho" no sustenta por si solo
  "tristeza devastadora y extremadamente profunda".
- Los ejemplos anteriores son fronteras semanticas, NO patrones
  lexicales ni frases que deban coincidir.
- Si el componente auditado es
  unsupported_emotion_attribution y proposed_value=false,
  confirma ese false cuando la auditoria completa no encuentre
  una emocion o intensidad materialmente no sustentada.
"""

    if code == "EM13":
        em1_audit_rule += """
ADJUDICACION METODOLOGICA EM13 ? 2026-10-12:
- EM13 es GENERAL. No exigir creencias explicitas para auditar ausencia de dano.
- Examina TODA la respuesta completa y evaluable, no solo las citas propuestas.
- Confirma ausencia de imposicion o descalificacion solo tras esa revision;
  busca tambien contradicciones contextuales relevantes.
- Si hay creencias, identidades o valores expresados, verifica ademas su respeto.
- Falta de menciones no demuestra ausencia verificada. Si no puedes resolver
  un componente, conserva ambiguous/unknown; nunca inventes evidencia ni puntajes.
"""

    conditional = ""

    if (
        code == "EM3"
        and component_name == "perspective_timing"
    ):
        conditional = """
REGLA EM3.perspective_timing:
- solo se activa si external_perspective_present=true;
- si external_perspective_present=false, unknown puede estar
  correctamente sustentado como estado condicionado no activado;
- no conviertas ese unknown tecnico en ambiguedad.
"""

    return f"""
EVALIA - VERIFICACION SEMANTICA INDEPENDIENTE V2

INDICADOR:
{code}

CONSTRUCTO:
{EM_SPECS[code]["construct"]}

COMPONENTE:
{component_name}

DEFINICION:
{COMPONENT_DESCRIPTIONS[code][component_name]}

VALOR PROPUESTO:
{proposed_value}

EVIDENCIA DEL EXTRACTOR:
{_format_refs(evidence)}

CONTRAEVIDENCIA DEL EXTRACTOR:
{_format_refs(counterevidence)}

REGLA DE INFERENCIA CONTROLADA:
{CONTROLLED_INFERENCE_RULES[code]}

{em1_audit_rule}

COMPONENTES RELACIONADOS:
{sibling_text}

{conditional}

REGLAS:

1. Verifica independientemente el claim.
2. No confies en la conclusion ni reason del extractor.
3. Revisa el material original completo autorizado.
4. Nunca uses informacion futura.
5. Historial disponible NO significa historial obligatorio.
6. Usa historial solo si es semanticamente pertinente al constructo.
6A. RESOLUCION DE REFERENTES HISTORICOS MULTIPLES:
- Si una expresion actual puede referirse razonablemente a dos o
  mas antecedentes historicos y el claim puede verificarse SIN
  decidir cual de ellos es el referente unico, el claim puede ser
  supported.
- En ese caso NO selecciones arbitrariamente un antecedente como
  si fuera el unico referente resuelto.
- Conserva en supporting_evidence los antecedentes historicos
  plausibles que sean necesarios para representar fielmente la
  dependencia semantica del claim.
- Si el claim SI depende de identificar un antecedente concreto
  entre varios plausibles y el contexto no permite resolverlo
  responsablemente, devuelve ambiguous.
- Para decidir si el claim depende de esa resolucion, pregunta:
  ?cambiar de un antecedente plausible a otro cambia materialmente
  lo que el valor propuesto afirma sobre la respuesta?
- Si NO cambia materialmente el claim, no es necesario resolver
  un referente unico y supported puede ser correcto.
- Si SI cambia materialmente el claim, no basta con que la
  respuesta haya escogido una interpretacion que aparece en el
  historial. Debe existir sustento semantico para preferir esa
  interpretacion sobre las otras alternativas plausibles.
- En particular, si la respuesta convierte una referencia
  historicamente ambigua en una situacion concreta y el componente
  auditado afirma que esa interpretacion concreta fue comprendida,
  NO confirmes el claim solo porque la situacion elegida sea una
  de las posibilidades reales del historial.
- Si dos o mas interpretaciones incompatibles siguen siendo
  razonablemente posibles y elegir entre ellas es necesario para
  confirmar el valor propuesto, devuelve ambiguous.
- No conviertas automaticamente la existencia de varios
  antecedentes en ambiguous: la pregunta decisiva es si resolver
  uno de ellos es necesario para verificar el claim.
- Esta regla es semantica. No uses pronombres, palabras clave,
  distancia de turnos ni proximidad textual como reglas de
  desambiguacion.
7. proposed_value=true afirma presencia/cumplimiento.
8. proposed_value=false afirma ausencia/no cumplimiento.
9. proposed_value=unknown afirma imposibilidad responsable de resolver.

9A. POLARIDAD LOGICA OBLIGATORIA:
- Audita literalmente la proposicion:
  COMPONENTE = proposed_value.
- El nombre del componente puede estar formulado en positivo o
  en negativo. NO inviertas su significado.
- Si proposed_value=false, el claim auditado es que la propiedad
  definida por ESE componente es falsa.
- Por ejemplo, si un componente pregunta si algo es
  generic_only y proposed_value=false, debes decidir si
  realmente NO es generic_only.
- Si concluyes semanticamente que el componente es false,
  devuelve supported.
- Si concluyes semanticamente que el componente es true,
  devuelve unsupported.
- No confundas 'el componente describe una propiedad negativa'
  con 'proposed_value=false'.
- Tu reason y tu status deben expresar la MISMA conclusion.
- Antes de devolver JSON, realiza esta comprobacion final:
  (a) que valor del componente conclui;
  (b) coincide con proposed_value;
  (c) si coincide -> supported;
  (d) si contradice -> unsupported;
  (e) si no puede resolverse responsablemente -> ambiguous.
- Esta comprobacion NO permite cambiar la definicion del
  componente, la rubrica ni las reglas de inferencia.

9B. CONTROL FINAL DE CONSISTENCIA DEL DICTAMEN:
- Antes de emitir status, determina de forma independiente
  el valor semantico del componente usando el material autorizado.
- Compara ese valor con proposed_value.
- Si ambos coinciden y la evidencia es suficiente,
  el status debe ser supported.
- Si se contradicen con evidencia suficiente,
  el status debe ser unsupported.
- Si no hay sustento suficiente para decidir,
  el status debe ser ambiguous.
- La razon escrita y el status deben expresar la misma conclusion.
- Nunca devuelvas unsupported mientras afirmas que el valor
  propuesto coincide con tu conclusion semantica.
- Nunca devuelvas supported mientras afirmas que el valor
  propuesto queda contradicho.
- Esta comprobacion no permite cambiar valores, inventar
  evidencia, reinterpretar componentes ni asignar puntuaciones.

9C. SIGNIFICADO LOGICO DE generic_only:
- Para un componente denominado
  frame_understanding_is_generic_only,
  true significa que la comprension se limita
  a formulaciones genericas, vagas o minimas.
- false significa que la comprension NO se limita
  a ese nivel generico.
- Una comprension concreta, contextualizada y
  sustentada de la situacion de la persona
  contradice generic_only=true y puede
  sustentar generic_only=false.
- No inviertas este significado al verificar.
- Si proposed_value=false y la evidencia demuestra
  comprension concreta no meramente generica,
  devuelve supported cuando el soporte sea suficiente.
- Si la evidencia demuestra comprension solamente
  generica, proposed_value=false no esta sustentado.
- Si la evidencia es insuficiente o ambigua,
  conserva la incertidumbre correspondiente.
- No confundas frame_understanding_is_clear con
  frame_understanding_is_generic_only: verifica
  cada componente segun su propia definicion.
- No inventes evidencia ni cambies la rubrica,
  la aplicabilidad o las puntuaciones.

10. supported confirma EL VALOR PROPUESTO.
11. unsupported significa que el valor propuesto no se sostiene.
12. ambiguous significa que tu auditoria independiente encuentra
    ambiguedad genuina que impide confirmar o refutar.
13. Para false debes auditar el ambito completo pertinente. Una
    ausencia puede estar supported con supporting_evidence=[].
14. NO inventes una cita para demostrar ausencia.
15. Una cita existente literalmente NO implica soporte semantico.
16. Una inferencia solo es valida dentro de las reglas del indicador.
17. No mezcles constructos.
18. No puntues ni sugieras 0/1/2/3/N/A.
19. Toda cita devuelta debe ser substring literal exacto.
20. source="history" exige history_index exacto del mensaje.
21. source="user" y source="response" exigen history_index=null.
22. No devuelvas history_role; el rol se deriva del historial.
23. No atribuyas al usuario actual algo dicho por assistant historico.
24. No rescates una cita buscandola en otro turno o fuente.
25. Si proposed_value=unknown pero puedes resolver razonablemente
    true o false, devuelve unsupported.
26. Si el contexto admite dos interpretaciones genuinas no
    resolubles, ambiguous es apropiado.

27. Si el claim depende de resolver semanticamente una referencia
    del turno actual mediante informacion del historial, debes
    comprobar el mensaje historico que resuelve ese referente.

28. Si el extractor afirma una interpretacion historicamente
    dependiente pero solo aporta una expresion referencial del
    turno actual y omite el antecedente necesario, NO consideres
    esa evidencia suficiente por si sola.

29. En ese caso revisa independientemente el historial autorizado.
    Si existe un antecedente claro y pertinente que sustenta el
    claim, puedes devolver supported, pero debes incluir en
    supporting_evidence la evidencia source="history" con el
    history_index exacto que sustenta la resolucion.

30. Si el antecedente historico es ambiguo o existen multiples
    referentes plausibles no resolubles, devuelve ambiguous.

31. Si el turno actual ya contiene toda la informacion concreta
    necesaria, no exijas ni agregues historial innecesario.

32. La resolucion de referentes es semantica, no lexical.
    No conviertas palabras como "eso" en disparadores automaticos.

================ HISTORIAL PREVIO =================
{history_text}

================ USUARIO ACTUAL ====================
{user_message}

================ RESPUESTA ACTUAL ==================
{ai_response}

================ FIN ===============================

Devuelve exclusivamente JSON conforme al schema.
""".strip()


def verify_component_semantics_v2(
    *,
    indicator_code: str,
    component_name: str,
    proposed_value: str,
    evidence: list[dict[str, Any]],
    counterevidence: list[dict[str, Any]],
    prior_history: Sequence[
        HistoryMessage | Mapping[str, object]
    ] | None = None,
    user_message: str = "",
    ai_response: str = "",
    sibling_components: dict[str, str] | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:

    history = normalize_prior_history(prior_history)

    # Literalidad del extractor ANTES del modelo.
    component = {
        "value": proposed_value,
        "evidence": evidence,
        "counterevidence": counterevidence,
        "reason": "",
    }

    literal = validate_component_evidence_v2(
        component,
        prior_history=history,
        user_message=user_message,
        ai_response=ai_response,
    )

    if not literal["evidence_valid"]:
        return {
            "status": "unsupported",
            "reason": (
                "Extractor evidence is not literal in the "
                "declared source."
            ),
            "supporting_evidence": [],
            "contradicting_evidence": [],
            "verification_error":
                "invalid_extractor_evidence",
        }

    if not literal["counterevidence_valid"]:
        return {
            "status": "unsupported",
            "reason": (
                "Extractor counterevidence is not literal in "
                "the declared source."
            ),
            "supporting_evidence": [],
            "contradicting_evidence": [],
            "verification_error":
                "invalid_extractor_counterevidence",
        }

    prompt = build_verification_prompt_v2(
        indicator_code=indicator_code,
        component_name=component_name,
        proposed_value=proposed_value,
        evidence=evidence,
        counterevidence=counterevidence,
        prior_history=history,
        user_message=user_message,
        ai_response=ai_response,
        sibling_components=sibling_components,
    )

    result = run_structured_semantic(
        prompt=prompt,
        schema=VERIFIER_SCHEMA_V2,
        provider=provider,
        model=model,
    )

    def _literal_checks(
        candidate: dict[str, Any],
    ) -> tuple[list[Any], list[Any]]:

        support = verify_evidence_refs(
            candidate["supporting_evidence"],
            prior_history=history,
            user_message=user_message,
            ai_response=ai_response,
        )

        contradiction = verify_evidence_refs(
            candidate["contradicting_evidence"],
            prior_history=history,
            user_message=user_message,
            ai_response=ai_response,
        )

        return support, contradiction

    support_checks, contradiction_checks = (
        _literal_checks(result)
    )

    verifier_evidence_valid = (
        all(x.valid for x in support_checks)
        and all(
            x.valid
            for x in contradiction_checks
        )
    )

    if not verifier_evidence_valid:

        retry_prompt = (
            prompt
            + """

================ RETRY DE LITERALIDAD ================

La salida anterior de esta verificacion no pudo superar
la validacion literal deterministica de evidencia.

Realiza NUEVAMENTE la verificacion semantica independiente
del claim usando exclusivamente el contexto autorizado.

IMPORTANTE:
- No asumas que el status anterior era correcto.
- Decide otra vez supported, unsupported o ambiguous.
- Toda quote que devuelvas debe copiarse EXACTAMENTE,
  caracter por caracter, como substring literal de la
  fuente declarada.
- No corrijas ortografia.
- No normalices tildes.
- No cambies signos.
- No reconstruyas frases.
- No combines fragmentos separados.
- source="history" exige el history_index exacto.
- source="user" y source="response" exigen
  history_index=null.
- Si una afirmacion de ausencia puede verificarse sin
  cita positiva, no inventes evidencia para llenarla.
- Si no puedes devolver evidencia literal valida para
  sustentar tu conclusion, conserva la incertidumbre
  semanticamente apropiada sin fabricar citas.

Devuelve exclusivamente JSON conforme al mismo schema.
""".strip()
        )

        result = run_structured_semantic(
            prompt=retry_prompt,
            schema=VERIFIER_SCHEMA_V2,
            provider=provider,
            model=model,
        )

        support_checks, contradiction_checks = (
            _literal_checks(result)
        )

        verifier_evidence_valid = (
            all(
                x.valid
                for x in support_checks
            )
            and all(
                x.valid
                for x in contradiction_checks
            )
        )

    if not verifier_evidence_valid:
        return {
            "status": "ambiguous",
            "reason": (
                "Verifier returned evidence that is not literal "
                "in its declared source after one controlled retry."
            ),
            "supporting_evidence": [],
            "contradicting_evidence": [],
            "verification_error":
                "invalid_verifier_evidence",
        }

    return {
        "status": result["status"],
        "reason": result["reason"],
        "supporting_evidence":
            result["supporting_evidence"],
        "contradicting_evidence":
            result["contradicting_evidence"],
        "verification_error": None,
    }
