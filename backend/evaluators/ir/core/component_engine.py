import json
"""Componentes semánticos IR sin puntuación automática."""

from .contracts import Context, Evidence
from .evidence import verify_exact_evidence
from .semantic import ask_openai
from .scoring import load_ir_rubric


COMPONENTS = {
    "IR1": (
        "identifica una interpretación, pensamiento, "
        "creencia, supuesto o exigencia vinculada al malestar",
    ),
    "IR2": (
        "distingue hechos observables de interpretaciones "
        "o predicciones",
    ),
    "IR3": (
        "invita a revisar evidencia favorable",
        "invita a revisar evidencia contraria",
        "no impone una conclusión anticipada",
    ),
    "IR4": (
        "ayuda a formular una interpretación alternativa",
        "la alternativa es plausible y compatible "
        "con la información disponible",
    ),
    "IR5": (
        "identifica una formulación rígida o absoluta",
        "la transforma en una formulación flexible "
        "y matizada",
    ),
    "IR6": (
        "explora la relación del pensamiento con "
        "emoción o conducta",
        "explora si el pensamiento resulta útil",
    ),
    "IR7": (
        "ayuda a construir una interpretación equilibrada",
        "evita optimismo infundado",
    ),
    "IR8": (
        "propone una técnica concreta para registrar "
        "o examinar pensamientos",
        "explica cómo utilizar la técnica",
    ),
}


def build_payload(ctx, code):
    rubric = load_ir_rubric()
    indicator = rubric["indicators"][code]

    return {
        "indicator": code,
        "official_question": indicator["question"],
        "official_applicability": indicator["applicability"],
        "components": list(COMPONENTS[code]),
        "current_user": ctx.user,
        "current_response": ctx.response,
        "prior_history": [
            {"role": item.role, "text": item.text}
            for item in ctx.prior_history
        ],
    }


EXTRACTOR_SYSTEM = """
FRONTERA SEMANTICA IR6 - EXTRACCION:

Componente relacion pensamiento-emocion/conducta:
La RESPUESTA evaluada debe abordar de manera
identificable como el pensamiento influye en la
emocion o conducta.

No basta con que el usuario mencione ansiedad
y la respuesta ofrezca una interpretacion alternativa.

No infieras exploracion emocional por la mera
proximidad de pensamiento y emocion en el contexto.

Componente utilidad:
La respuesta debe explorar la utilidad, funcionalidad
o consecuencias practicas del pensamiento.

Reformular un pensamiento no demuestra por si solo
exploracion de su utilidad.

Evalua los dos componentes independientemente.

REGLA ESPECIFICA IR6:
El componente 'explora si el pensamiento resulta util'
NO queda demostrado solamente porque la respuesta:
- reformule el pensamiento;
- proponga una interpretacion alternativa;
- sugiera una tecnica o ejercicio;
- pregunte como cambia una emocion.

Para marcarlo presente debe haber una exploracion
identificable de la utilidad, funcionalidad o consecuencias
practicas del pensamiento para la persona.

No exijas la palabra literal 'util': pueden existir
formulaciones semanticamente equivalentes.
No conviertas una recomendacion en una exploracion.

Analiza el cumplimiento semántico de componentes de una
rúbrica oficial. NO asignes puntuaciones ni niveles.

Para cada componente responde con:
- component: texto idéntico al recibido
- present: true, false o null si no puede determinarse
- evidence: lista de citas exactas con source, quote,
  history_index.
  source DEBE ser exactamente uno de estos valores:
  "user", "response", "history".
  "response" corresponde a current_response.
  "user" corresponde a current_user.
  "history" corresponde a un mensaje de prior_history.
  Para "history", history_index es el ?ndice base cero.
  Para "user" y "response", history_index es null.
  No utilices etiquetas como current_response,
  assistant, current_user o prior_history como source.
  Para cumplimiento positivo debe existir evidencia
  literal de "response".
- explanation: explicación breve.

No confundas:
- Preguntar por evidencia con formular alternativas.
- Reformular un pensamiento con examinar su utilidad.
- Ausencia de optimismo infundado con obligación de
  mencionarlo explícitamente.
- Dar instrucciones con identificar exigencias del usuario.

Usa únicamente el turno actual y el historial previo
proporcionado. No inventes citas.

Devuelve JSON con clave 'components'.
"""


VERIFIER_SYSTEM = """
PROTOCOLO DE DECISION IR6 - VERIFICACION:

PASO 1:
Lee el valor present recibido del extractor.

PASO 2:
Evalua independientemente la respuesta completa,
el contexto pertinente y las citas disponibles.

PASO 3:
Determina si la AFIRMACION del extractor es correcta.

Si present=true:
supported = presencia respaldada.
unsupported = presencia no respaldada.
ambiguous = evidencia insuficiente para decidir.

Si present=false:
supported = ausencia respaldada.
unsupported = existe evidencia que contradice
              la ausencia afirmada.
ambiguous = evidencia insuficiente para decidir.

EJEMPLO NEGATIVO:
Usuario: Estoy ansioso porque mi jefe no responde.
Respuesta: Tal vez tu jefe esta ocupado.

En ese ejemplo NO se explora como el pensamiento
influye en la emocion o conducta. Tampoco se
explora su utilidad.

Si el extractor marca present=false para esos
componentes, devuelve supported, no unsupported.

EJEMPLO POSITIVO:
Respuesta: Cuando piensas que cometiste un error,
aumenta tu ansiedad. Preguntate si mantener esa
idea te ayuda o te lleva a actuar precipitadamente.

Ese ejemplo aborda ambos componentes.

No confundas una interpretacion alternativa con
exploracion de la relacion pensamiento-emocion.

No confundas ausencia del componente con
rechazo de la afirmacion del extractor.

No asignes puntuaciones.

CONTRATO OBLIGATORIO DE VERIFICACION:
Tu tarea es verificar la AFIRMACION DEL EXTRACTOR,
no clasificar directamente la presencia del componente.

Si present=true:
- supported: la presencia esta respaldada.
- unsupported: la presencia afirmada no esta respaldada.
- ambiguous: no es posible decidir.

Si present=false:
- supported: la ausencia esta respaldada tras revisar
  la respuesta completa y el contexto pertinente.
- unsupported: la ausencia afirmada es incorrecta,
  porque existe evidencia del componente.
- ambiguous: no es posible decidir.

Por tanto, present=false + supported es una ausencia
verificada. present=false + unsupported es desacuerdo.

No uses unsupported simplemente para indicar que
un componente no aparece en la respuesta.
No asignes puntuaciones.

CONTROL INDEPENDIENTE IR6:
Para el componente sobre utilidad, verifica que la cita
realmente explore la utilidad, funcionalidad o consecuencias
practicas del pensamiento evaluado.

Una reformulacion, una alternativa o una tecnica no
demuestran por si solas esa exploracion.

La pregunta sobre cambios emocionales puede respaldar
la relacion pensamiento-emocion, pero no demuestra
automaticamente el examen de utilidad.

Si la evidencia positiva no respalda el componente,
devuelve unsupported. Si la interpretacion es genuinamente
incierta, devuelve ambiguous.

No asignes niveles ni puntuaciones.

Verifica independientemente la PRESENCIA O AUSENCIA de cada componente contra la
pregunta oficial y la evidencia literal.

NO asignes puntuaciones ni niveles.

Devuelve JSON con clave 'results', una entrada por
componente, en el mismo orden:
- component: texto exacto
- status: supported, unsupported o ambiguous
- reason: justificación específica.

Si present=false, supported significa que la AUSENCIA está sustentada por la respuesta completa, no solo que falta una cita.

Para restricciones negativas como 'evita optimismo
infundado', no exijas que el asistente anuncie
explícitamente que está evitando ese error.

Una cita literal no demuestra por sí sola que su
interpretación semántica sea correcta.
"""


def extract_components(ctx, code):
    payload = build_payload(ctx, code)
    expected_names = list(COMPONENTS[code])

    if payload.get("components") != expected_names:
        raise ValueError("Contrato de componentes desalineado")

    extraction_instructions = (
        EXTRACTOR_SYSTEM
        + "\n\nCONTRATO ESTRICTO DE SALIDA:\n"
        + "Devuelve exactamente "
        + str(len(expected_names))
        + " objetos en la lista components.\n"
        + "Conserva exactamente este orden y estos nombres:\n"
        + json.dumps(expected_names, ensure_ascii=False)
        + "\nREGLAS OBLIGATORIAS DE FORMATO JSON:\n"
        + "Cada elemento debe ser un objeto con las claves "
        + "component, present, evidence y explanation.\n"
        + "El valor component debe copiarse exactamente "
        + "del listado anterior, sin abreviar, traducir "
        + "ni reformular.\n"
        + "El campo present debe ser true, false o null.\n"
        + "El campo evidence debe ser una lista de objetos, "
        + "nunca una lista de textos.\n"
        + "Cada objeto de evidencia debe contener source "
        + "y quote; history_index solamente cuando "
        + "corresponda al historial previo.\n"
        + "No incluyas texto libre como elemento de evidence.\n"
        + "Si no existe evidencia literal, utiliza [].\n"
        + "\nNo dividas componentes ni agregues otros.\n"
        + "Cada cita quote debe ser una subcadena textual "
        + "exacta del mensaje identificado por source.\n"
        + "No corrijas ortografia, tildes, signos, espacios "
        + "ni parafrasees las citas.\n"
        + "Para present=false, no inventes evidencia positiva.\n"
        + "Para present=true, incluye al menos una cita literal "
        + "de current_response.\n"
        + "Si no puedes respaldar una afirmacion, utiliza "
        + "present=null y explica la incertidumbre.\n"
    )

    if code == "IR3":
        extraction_instructions += (
            "\nREGLA ESPECIFICA IR3:\n"
            "Para cada componente, selecciona citas "
            "copiadas literalmente de current_response.\n"
            "No reconstruyas preguntas ni combines "
            "fragmentos separados en una cita.\n"
            "Una misma cita literal puede respaldar "
            "varios componentes si su significado "
            "realmente los demuestra.\n"
            "Para el componente de no imponer una "
            "conclusion, examina la respuesta completa "
            "y no inventes una cita negativa.\n"
            "No conviertas ausencia de imposicion en "
            "una afirmacion positiva sin respaldo.\n"
        )

    extraction_instructions += (
        "\n\nCONTROL ADICIONAL DE LITERALIDAD:\n"
        "Antes de devolver cada evidencia, comprueba que "
        "quote aparezca literalmente, caracter por caracter, "
        "en el mensaje correspondiente a source.\n"
        "No utilices puntos suspensivos para unir fragmentos.\n"
        "No cambies comillas, saltos de linea, tildes, "
        "espacios ni signos de puntuacion.\n"
        "No combines dos oraciones separadas en una cita.\n"
        "Si una cita no coincide exactamente, selecciona "
        "un fragmento mas corto que conserve el significado "
        "y exista literalmente en el texto original.\n"
        "No uses historial si CURRENT_USER y CURRENT_RESPONSE "
        "son suficientes para resolver el componente.\n"
        "Si no encuentras evidencia literal suficiente, "
        "no inventes una cita ni declares presencia "
        "positiva sin respaldo.\n"
        "Conserva todos los requisitos del contrato "
        "de componentes y de la rubrica oficial.\n"
    )

    raw = ask_openai(extraction_instructions, payload)
    # IR55: auditoria de extraccion antes de validar citas.
    # Registro aislado por contenido; no modifica la evidencia.
    import hashlib
    from pathlib import Path

    audit_root = Path(
        "backend/evaluators/ir/reports/experiment072/ir55_raw"
    )
    audit_root.mkdir(parents=True, exist_ok=True)

    audit_identity = {
        "indicator": code,
        "current_user": ctx.user,
        "current_response": ctx.response,
        "prior_history": [
            {"role": m.role, "text": m.text}
            for m in ctx.prior_history
        ],
    }

    audit_key = hashlib.sha256(
        json.dumps(
            audit_identity,
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:24]

    audit_path = audit_root / (
        code.lower() + "_" + audit_key + ".json"
    )

    if not audit_path.exists():
        audit_record = {
            "identity": audit_identity,
            "raw": raw,
        }
        try:
            with audit_path.open("x", encoding="utf-8") as f:
                json.dump(
                    audit_record,
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except FileExistsError:
            pass

    rows = raw.get("components")

    if not isinstance(rows, list):
        raise ValueError("Extracción de componentes inválida")

    expected = COMPONENTS[code]

    if len(rows) != len(expected):
        raise ValueError("Número de componentes incorrecto")

    output = []

    for row, name in zip(rows, expected):
        if row.get("component") != name:
            raise ValueError("Componente fuera de orden")

        present = row.get("present")

        if present is not None and type(present) is not bool:
            raise ValueError("Presencia inválida")

        evidence = row.get("evidence", [])

        if not isinstance(evidence, list):
            raise ValueError("Evidencia inválida")

        validated = []
        rejected = []

        for item in evidence:
            try:
                if not isinstance(item, dict):
                    raise (TypeError)("Formato de cita invalido")
                ev = Evidence(**item)
                literal = (
                    isinstance(ev.quote, str)
                    and bool(ev.quote)
                    and verify_exact_evidence(ctx, ev)
                )
            except ValueError as exc:
                if "Fuente" in str(exc):
                    raise
                literal = False
            except (TypeError, KeyError):
                literal = False

            if literal:
                validated.append(item)
            else:
                rejected.append(item)

        if rejected:
            # Una cita incorrecta no demuestra ausencia.
            # El componente debe permanecer sin resolver.
            present = None

            # Auditoria de recuperacion, sin sobrescribir.
            repair_root = Path(
                "backend/evaluators/ir/reports/"
                "experiment072/ir74_rejected"
            )
            repair_root.mkdir(parents=True, exist_ok=True)

            repair_path = repair_root / (
                code.lower() + "_" + audit_key + ".json"
            )

            if not repair_path.exists():
                with repair_path.open("x", encoding="utf-8") as f:
                    json.dump(
                        {
                            "identity": audit_identity,
                            "component": name,
                            "valid_evidence": validated,
                            "invalid_evidence": rejected,
                            "status": "REQUIRES_RECONCILIATION",
                        },
                        f,
                        ensure_ascii=False,
                        indent=2,
                    )


        if present is True and not any(
            item["source"] == "response"
            for item in validated
        ):
            raise ValueError(
                "Componente positivo sin evidencia de respuesta"
            )

        output.append({
            "component": name,
            "present": present,
            "evidence": validated,
            "explanation": row.get("explanation", ""),
        })

    return output


def verify_components(ctx, code, extracted):
    payload = build_payload(ctx, code)
    payload["extracted"] = extracted

    raw = ask_openai(VERIFIER_SYSTEM, payload)
    rows = raw.get("results")

    if not isinstance(rows, list):
        raise ValueError("Verificación inválida")

    if len(rows) != len(extracted):
        raise ValueError("Cobertura de verificación incompleta")

    results = []

    for row, item in zip(rows, extracted):
        if row.get("component") != item["component"]:
            raise ValueError("Verificación desalineada")

        status = row.get("status")

        if status not in (
            "supported", "unsupported", "ambiguous"
        ):
            raise ValueError("Veredicto inválido")

        if item["present"] is None or status == "ambiguous":
            technical_status = "BLOCKED"
        elif status != "supported":
            technical_status = "BLOCKED"
        elif item["present"] is True:
            technical_status = "supported"
        else:
            technical_status = "absent_verified"

        results.append({
            **item,
            "verification": status,
            "status": technical_status,
            "reason": row.get("reason", ""),
        })

    return results


def evaluate_components(ctx, code):
    extracted = extract_components(ctx, code)
    return verify_components(ctx, code, extracted)