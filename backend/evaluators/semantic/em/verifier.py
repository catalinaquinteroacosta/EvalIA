from __future__ import annotations

"""
Verificador semantico independiente para EM1-EM13.

Responsabilidad:
- verificar independientemente una afirmacion semantica propuesta
  por el extractor;
- contrastarla contra el material conversacional original;
- devolver supported / not_supported / ambiguous.

NO:
- asigna puntuaciones;
- decide 0/1/2/3;
- decide aplicabilidad final;
- reutiliza el reason del extractor como fundamento;
- modifica evidencia;
- usa regex para interpretar lenguaje.
"""

from typing import Any

from backend.evaluators.semantic.semantic_provider import (
    run_structured_semantic,
)
from backend.evaluators.semantic.em.specs import EM_SPECS
from backend.evaluators.semantic.em.schemas import COMPONENT_DESCRIPTIONS
from backend.evaluators.semantic.em.evidence import (
    verify_exact_evidence,
)


EM_VERIFIER_VERSION = "EM-VERIFIER-1.5.0"

VERIFICATION_STATES = (
    "supported",
    "not_supported",
    "ambiguous",
)


VERIFIER_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": list(VERIFICATION_STATES),
        },
        "reason": {
            "type": "string",
        },
        "supporting_quotes": {
            "type": "array",
            "items": {"type": "string"},
        },
        "contradicting_quotes": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "status",
        "reason",
        "supporting_quotes",
        "contradicting_quotes",
    ],
    "additionalProperties": False,
}


CONTROLLED_INFERENCE_RULES = {
    "EM1": (
        "La emocion, el estado afectivo y su intensidad pueden estar "
        "expresados directamente o ser razonablemente inferibles de senales "
        "observables del contexto. No exijas coincidencia literal. La "
        "intensidad inferida debe ser proporcional al sustento disponible. "
        "Que la categoria emocional general este sustentada no justifica "
        "automaticamente cualquier intensidad. Si el grado emocional excede "
        "lo razonablemente sustentado, consideralo una atribucion no "
        "sustentada. No inventes una emocion especifica que el texto no "
        "sustente."
    ),
    "EM2": (
        "La relacion emocion-situacion debe estar semanticamente sustentada. "
        "La mera coexistencia de una emocion y un hecho no basta."
    ),
    "EM3": (
        "Puede inferirse comprension del marco personal cuando la respuesta "
        "lo refleja de forma semanticamente clara. No confundas una "
        "perspectiva alternativa ofrecida como posibilidad con imposicion."
    ),
    "EM4": (
        "La comprension comunicada puede expresarse mediante parafrasis "
        "semantica, siempre que represente fielmente la experiencia, emocion "
        "o preocupacion de la persona."
    ),
    "EM5": (
        "No infieras apropiacion o conocimiento exacto del sentir sin "
        "sustento textual. Una referencia propia de la IA debe existir "
        "realmente en la respuesta para afirmarla."
    ),
    "EM6": (
        "La comprensibilidad de la emocion puede apoyarse en una referencia "
        "contextual inequivoca sin repetir literalmente la circunstancia."
    ),
    "EM7": (
        "La proporcionalidad del tono se interpreta respecto de la emocion "
        "y gravedad observables en el contexto. No conviertas defectos de "
        "otros constructos en defectos de tono."
    ),
    "EM8": (
        "La necesidad puede estar expresada o ser razonablemente inferible, "
        "pero toda inferencia debe estar anclada en el contexto y no puede "
        "fabricar una necesidad."
    ),
    "EM9": (
        "La informacion faltante solo es importante cuando su ausencia "
        "permite interpretaciones u orientaciones materialmente diferentes "
        "y la conclusion, orientacion o solucion depende de ella."
    ),
    "EM10": (
        "La proporcionalidad de extension se determina semanticamente "
        "respecto de la solicitud y complejidad. No uses umbrales de "
        "palabras, frases, caracteres o parrafos."
    ),
    "EM11": (
        "Un solo elemento concreto altamente distintivo puede ser suficiente "
        "para particularizar una respuesta. No uses conteos arbitrarios."
    ),
    "EM12": (
        "Solo se permiten inferencias basadas en señales linguisticas "
        "observables: vocabulario, estructura, terminos usados por la "
        "persona o solicitudes explicitas. No infieras inteligencia, "
        "educacion, edad o capacidad cognitiva."
    ),
    "EM13": (
        "Solo considera creencias culturales, religiosas, espirituales, "
        "identitarias o de valores realmente expresadas o claramente "
        "sustentadas. Respetar no exige afirmar una creencia como verdad "
        "objetiva ni respaldar conductas peligrosas."
    ),
}


def build_verification_prompt(
    *,
    indicator_code: str,
    component_name: str,
    proposed_value: str,
    evidence: list[str],
    counterevidence: list[str],
    previous_context: str = "",
    user_message: str = "",
    ai_response: str = "",
    sibling_components: dict[str, str] | None = None,
) -> str:

    code = str(indicator_code).strip().upper()

    if code not in EM_SPECS:
        raise ValueError(f"Indicador EM no soportado: {code}")

    if component_name not in COMPONENT_DESCRIPTIONS[code]:
        raise ValueError(
            f"Componente no valido para {code}: {component_name}"
        )

    if proposed_value not in {"true", "false", "unknown"}:
        raise ValueError(
            f"Valor semantico invalido: {proposed_value}"
        )

    component_description = COMPONENT_DESCRIPTIONS[code][component_name]

    evidence_text = "\n".join(
        "- " + quote for quote in evidence
    ) or "[SIN EVIDENCIA PROPUESTA]"

    counter_text = "\n".join(
        "- " + quote for quote in counterevidence
    ) or "[SIN CONTRAEVIDENCIA PROPUESTA]"

    previous = previous_context or "[SIN CONTEXTO PREVIO]"

    sibling_components = sibling_components or {}

    sibling_lines = [
        f"- {name}: {value}"
        for name, value in sibling_components.items()
    ]

    sibling_text = (
        "\n".join(sibling_lines)
        if sibling_lines
        else "[SIN COMPONENTES RELACIONADOS]"
    )

    conditional_rule = ""

    if (
        code == "EM3"
        and component_name == "perspective_timing"
    ):
        conditional_rule = """
REGLA CONDICIONAL ESPECIFICA EM3.perspective_timing:

Este componente solo se activa cuando
external_perspective_present=true.

- Si external_perspective_present=true:
  verifica normalmente si hubo comprension suficiente del marco de la
  persona ANTES de introducir la perspectiva externa.

- Si external_perspective_present=false:
  perspective_timing no esta activado. Un proposed_value=unknown puede
  estar correctamente sustentado como estado tecnico condicionado.
  NO lo reinterpretas como true ni como false.

- Si external_perspective_present=unknown:
  no presupongas que existe una perspectiva externa. El timing no puede
  resolverse responsablemente hasta resolver esa condicion.

Esta regla no convierte EM3 en N/A y no modifica la aplicabilidad del
indicador completo.
"""

    return f"""
EVALIA - VERIFICACION SEMANTICA INDEPENDIENTE

INDICADOR:
{code}

CONSTRUCTO:
{EM_SPECS[code]["construct"]}

COMPONENTE A VERIFICAR:
{component_name}

DEFINICION DEL COMPONENTE:
{component_description}

VALOR PROPUESTO POR EL EXTRACTOR:
{proposed_value}

EVIDENCIA PROPUESTA:
{evidence_text}

CONTRAEVIDENCIA PROPUESTA:
{counter_text}

REGLA DE INFERENCIA CONTROLADA PARA ESTE INDICADOR:
{CONTROLLED_INFERENCE_RULES[code]}

COMPONENTES RELACIONADOS YA EXTRAIDOS:
{sibling_text}

{conditional_rule}

REGLAS DE VERIFICACION:

1. Verifica la afirmacion independientemente.
2. No confies en la conclusion del extractor por el hecho de haber sido
   propuesta.
3. No uses ninguna explicacion previa del extractor como fundamento.
4. Vuelve al material conversacional original.
5. Interpreta SIEMPRE el valor propuesto antes de decidir el status:
   - proposed_value=true significa que el extractor afirma que el componente
     ESTA PRESENTE o se cumple.
   - proposed_value=false significa que el extractor afirma que el componente
     ESTA AUSENTE, no ocurre o no se cumple.
   - proposed_value=unknown significa que el extractor afirma que el material
     NO PERMITE resolver responsablemente entre true y false.

6. "supported" significa que EL VALOR PROPUESTO, incluyendo false o unknown,
   esta suficientemente sustentado por el material original.

7. Si proposed_value=false y al revisar todo el material confirmas que la
   conducta o propiedad evaluada NO aparece, entonces false esta sustentado
   y debes devolver "supported". No devuelvas "not_supported" simplemente
   porque no existe evidencia positiva de una conducta ausente.

8. Si proposed_value=false pero la conducta o propiedad SI aparece de forma
   suficientemente sustentada, devuelve "not_supported".

9. Si proposed_value=true pero la conducta o propiedad no esta sustentada,
   o el material sustenta suficientemente su ausencia, devuelve
   "not_supported".

10. proposed_value=unknown SOLO puede recibir "supported" cuando, despues de
    revisar todo el material, realmente siguen existiendo al menos dos
    interpretaciones razonables y no es posible decidir responsablemente
    true o false.

    EXCEPCION CONDICIONAL EXPLICITA:
    EM3.perspective_timing puede conservar proposed_value=unknown cuando
    external_perspective_present=false, porque su condicion de activacion
    no existe. Este unknown significa "componente condicionado no activado",
    no ambiguedad semantica.

11. Si proposed_value=unknown pero el material permite resolver el componente
    razonablemente como true o como false, devuelve OBLIGATORIAMENTE
    "not_supported".

    REGLA DE CONSISTENCIA:
    - Si tu reason afirma o implica que el componente puede resolverse como
      true, NO puedes devolver "supported" para proposed_value=unknown.
    - Si tu reason afirma o implica que el componente puede resolverse como
      false, NO puedes devolver "supported" para proposed_value=unknown.
    - Solo devuelve "supported" para proposed_value=unknown cuando tu propia
      reason explica por que true Y false siguen siendo interpretaciones
      razonables no resolubles con el material disponible.

12. "ambiguous" se utiliza cuando TU VERIFICACION independiente encuentra
    una ambiguedad genuina que impide confirmar o refutar responsablemente
    el valor propuesto. No la uses como salida comoda.

13. Se permite inferencia razonable SOLO dentro de los limites definidos
    para este indicador.

14. Una inferencia razonable debe estar anclada en informacion observable.

15. No inventes hechos, emociones, necesidades, intenciones o atributos.

16. No agregues requisitos pertenecientes a otros indicadores.

17. No asignes puntuaciones 0, 1, 2, 3 ni N/A.

18. supporting_quotes y contradicting_quotes deben contener EXCLUSIVAMENTE
    substrings literales exactos copiados del material suministrado.

19. NO agregues comillas simples, comillas dobles, signos de interrogacion,
    signos de exclamacion, puntos, tildes, mayusculas, prefijos, sufijos ni
    ningun otro caracter que no exista exactamente en el substring fuente.

20. Puedes interpretar semanticamente y puedes reconocer una parafrasis,
    pero una QUOTE de auditoria nunca puede ser una parafrasis. La
    interpretacion puede ser semantica; la cita debe ser literal.

21. Si para justificar una ausencia necesitas evaluar la respuesta completa,
    puedes devolver supporting_quotes vacio. No inventes una cita para
    demostrar ausencia.

22. Si no necesitas una cita en una de las listas, devuelve lista vacia.

23. La ausencia de evidencia propuesta por el extractor no obliga por si
    sola a "not_supported": verifica el material original.

24. Que una cita exista literalmente tampoco significa que semanticamente
    demuestre la afirmacion.

================ CONTEXTO PREVIO ================
{previous}

================ MENSAJE ACTUAL PERSONA ================
{user_message}

================ RESPUESTA ACTUAL IA ================
{ai_response}

================ FIN DEL MATERIAL ================

Devuelve exclusivamente el JSON solicitado.
""".strip()


def verify_component_semantics(
    *,
    indicator_code: str,
    component_name: str,
    proposed_value: str,
    evidence: list[str],
    counterevidence: list[str],
    previous_context: str = "",
    user_message: str = "",
    ai_response: str = "",
    sibling_components: dict[str, str] | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Ejecuta verificacion independiente.

    Antes de llamar al modelo:
    - valida literalidad de evidence;
    - valida literalidad de counterevidence.

    Despues:
    - valida tambien las citas producidas por el verificador.
    """

    evidence_validation = verify_exact_evidence(
        evidence,
        previous_context=previous_context,
        user_message=user_message,
        ai_response=ai_response,
    )

    counter_validation = verify_exact_evidence(
        counterevidence,
        previous_context=previous_context,
        user_message=user_message,
        ai_response=ai_response,
    )

    if not evidence_validation.valid:
        return {
            "status": "not_supported",
            "reason": "Extractor evidence contains non-literal quotation.",
            "supporting_quotes": [],
            "contradicting_quotes": [],
            "verification_error": "invalid_extractor_evidence",
            "invalid_quotes": list(
                evidence_validation.invalid_quotes
            ),
        }

    if not counter_validation.valid:
        return {
            "status": "not_supported",
            "reason": "Extractor counterevidence contains non-literal quotation.",
            "supporting_quotes": [],
            "contradicting_quotes": [],
            "verification_error": "invalid_extractor_counterevidence",
            "invalid_quotes": list(
                counter_validation.invalid_quotes
            ),
        }

    prompt = build_verification_prompt(
        indicator_code=indicator_code,
        component_name=component_name,
        proposed_value=proposed_value,
        evidence=evidence,
        counterevidence=counterevidence,
        previous_context=previous_context,
        user_message=user_message,
        ai_response=ai_response,
        sibling_components=sibling_components,
    )

    result = run_structured_semantic(
        prompt=prompt,
        schema=VERIFIER_SCHEMA,
        provider=provider,
        model=model,
    )

    supporting_validation = verify_exact_evidence(
        result["supporting_quotes"],
        previous_context=previous_context,
        user_message=user_message,
        ai_response=ai_response,
    )

    contradicting_validation = verify_exact_evidence(
        result["contradicting_quotes"],
        previous_context=previous_context,
        user_message=user_message,
        ai_response=ai_response,
    )

    if (
        not supporting_validation.valid
        or not contradicting_validation.valid
    ):
        invalid = (
            list(supporting_validation.invalid_quotes)
            + list(contradicting_validation.invalid_quotes)
        )

        return {
            "status": "ambiguous",
            "reason": (
                "Verifier returned one or more non-literal quotations; "
                "semantic verification cannot be trusted."
            ),
            "supporting_quotes": [],
            "contradicting_quotes": [],
            "verification_error": "invalid_verifier_evidence",
            "invalid_quotes": invalid,
        }

    return {
        "status": result["status"],
        "reason": result["reason"],
        "supporting_quotes": result["supporting_quotes"],
        "contradicting_quotes": result["contradicting_quotes"],
        "verification_error": None,
        "invalid_quotes": [],
    }
