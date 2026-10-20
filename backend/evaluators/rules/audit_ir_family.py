"""
AUDITORÍA FAMILIAR IR1–IR8 · EvalIA

Objetivo:
- Auditar la familia AD-03 Reestructuración Cognitiva.
- Recorrer automáticamente el banco actual de escenarios.
- NO modificar reglas.
- NO modificar JSON.
- NO escribir en SQLite.
- NO alterar experimentos existentes.

IMPORTANTE:
El banco contiene mensajes del USUARIO, no respuestas reales de IA.

Por tanto, esta auditoría NO valida todavía el puntaje experimental
0–3 de una IA real. Su objetivo es estudiar:

1. comportamiento de aplicabilidad;
2. uso del contexto acumulado;
3. posibles N/A excesivos o insuficientes;
4. invariantes técnicas;
5. zonas semánticas que posteriormente requieran stress tests
   independientes con pares usuario + respuesta IA.

Los puntajes producidos usando una respuesta IA vacía son únicamente
diagnósticos internos y NO deben interpretarse como resultados
experimentales.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from backend.evaluators.evaluation_context import (
    EvaluationContext,
    ConversationTurn,
)
from backend.evaluators.rules.restructuring_rules import RestructuringRules


# ==============================================================
# CONFIGURACIÓN
# ==============================================================

ROOT = Path(__file__).resolve().parents[3]
PROMPTS_DIR = ROOT / "database" / "prompts"

IR_CODES = [f"IR{i}" for i in range(1, 9)]

EXPECTED_SCENARIOS = 38
EXPECTED_TURNS = 190


# ==============================================================
# CARGA DEL BANCO
# ==============================================================

def load_bank() -> list[dict[str, Any]]:
    """
    Lee todos los JSON almacenados en database/prompts.

    No modifica ningún archivo.
    """

    scenarios = []

    for path in sorted(PROMPTS_DIR.glob("*.json")):
        with path.open("r", encoding="utf-8-sig") as f:
            data = json.load(f)

        scenario = str(
            data.get("scenario", path.stem)
        ).strip()

        title = str(
            data.get("title", "")
        ).strip()

        category = str(
            data.get("category", "")
        ).strip()

        turns = data.get("turns", [])

        scenarios.append(
            {
                "scenario": scenario,
                "title": title,
                "category": category,
                "turns": turns,
                "path": path,
            }
        )

    return scenarios


# ==============================================================
# CONSTRUCCIÓN DEL CONTEXTO REAL DE EVALIA
# ==============================================================

def build_context(
    scenario: dict[str, Any],
    current_index: int,
    assistant_text: str,
) -> EvaluationContext:
    """
    Construye EvaluationContext usando la arquitectura real de EvalIA.

    Para cada turno auditado se incluyen los turnos desde T1 hasta
    el turno actual.

    Ejemplo:

        Auditoría T1 -> [T1]
        Auditoría T2 -> [T1, T2]
        Auditoría T3 -> [T1, T2, T3]
        ...

    Esto permite que las reglas puedan utilizar el contexto acumulado.

    Como el banco contiene estímulos del usuario y no respuestas
    experimentales de IA, los turnos anteriores reciben ai_response=""
    y el turno actual recibe assistant_text.

    En esta primera fase assistant_text también será vacío.
    """

    source_turns = scenario["turns"]

    conversation_turns: list[ConversationTurn] = []

    for idx in range(current_index + 1):

        source_turn = source_turns[idx]

        user_text = str(
            source_turn.get("user", "")
        ).strip()

        if idx == current_index:
            ai_text = assistant_text
        else:
            ai_text = "."

        conversation_turns.append(
            ConversationTurn(
                turn_number=int(
                    source_turn.get("id", idx + 1)
                ),
                user_message=user_text,
                ai_response=ai_text,
            )
        )

    return EvaluationContext(
        experiment_id=1,
        scenario_code=scenario["scenario"],
        rubric_type="trastorno",
        model_name="AUDITOR_IR",
        turns=conversation_turns,
        scenario_title=scenario.get("title", ""),
        scenario_category=scenario.get("category", ""),
        scenario_description="",
        metadata={
            "audit": True,
            "source": "database/prompts",
            "purpose": "IR family applicability stress audit",
        },
    )


# ==============================================================
# EJECUCIÓN DE UN INDICADOR
# ==============================================================

def evaluate_indicator(
    rules: RestructuringRules,
    indicator_code: str,
    context: EvaluationContext,
):
    """
    Intenta utilizar la interfaz pública disponible en
    RestructuringRules.

    No modifica las reglas.
    """

    if hasattr(rules, "evaluate"):
        return rules.evaluate(
            indicator_code,
            context,
        )

    if hasattr(rules, "evaluate_indicator"):
        return rules.evaluate_indicator(
            indicator_code,
            context,
        )

    method_name = f"evaluate_{indicator_code.lower()}"

    if hasattr(rules, method_name):
        return getattr(
            rules,
            method_name,
        )(context)

    raise AttributeError(
        "No se encontró una interfaz pública compatible en "
        "RestructuringRules para evaluar indicadores."
    )


# ==============================================================
# NORMALIZACIÓN DE RESULTADOS
# ==============================================================

def result_summary(result) -> dict[str, Any]:
    """
    Convierte IndicatorResult en una estructura cómoda
    para la auditoría sin alterar el objeto original.
    """

    return {
        "applicable": getattr(
            result,
            "applicable",
            None,
        ),

        "score": getattr(
            result,
            "score",
            None,
        ),

        "justification": getattr(
            result,
            "justification",
            "",
        ),

        "evidence": list(
            getattr(
                result,
                "evidence",
                [],
            ) or []
        ),

        "positive_checks": list(
            getattr(
                result,
                "positive_checks",
                [],
            ) or []
        ),

        "negative_checks": list(
            getattr(
                result,
                "negative_checks",
                [],
            ) or []
        ),

        "missing_checks": list(
            getattr(
                result,
                "missing_checks",
                [],
            ) or []
        ),

        "confidence": getattr(
            result,
            "confidence",
            None,
        ),

        "rule_version": getattr(
            result,
            "rule_version",
            "",
        ),
    }


# ==============================================================
# AUDITORÍA
# ==============================================================

def main() -> None:

    print("=" * 78)
    print("EVALIA · AUDITORÍA FAMILIAR AD-03 · IR1–IR8")
    print("=" * 78)

    # ----------------------------------------------------------
    # CARGAR BANCO
    # ----------------------------------------------------------

    scenarios = load_bank()

    total_turns = sum(
        len(s["turns"])
        for s in scenarios
    )

    print(
        f"\nBanco encontrado: "
        f"{len(scenarios)} escenarios / "
        f"{total_turns} turnos"
    )

    print(
        f"Directorio: {PROMPTS_DIR}"
    )

    # ----------------------------------------------------------
    # VALIDACIÓN ESTRUCTURAL DEL BANCO
    # ----------------------------------------------------------

    if len(scenarios) == EXPECTED_SCENARIOS:
        print(
            f"[OK] Cantidad de escenarios: "
            f"{EXPECTED_SCENARIOS}"
        )
    else:
        print(
            f"[ALERTA] Se esperaban "
            f"{EXPECTED_SCENARIOS} escenarios y se encontraron "
            f"{len(scenarios)}."
        )

    if total_turns == EXPECTED_TURNS:
        print(
            f"[OK] Cantidad total de turnos: "
            f"{EXPECTED_TURNS}"
        )
    else:
        print(
            f"[ALERTA] Se esperaban "
            f"{EXPECTED_TURNS} turnos y se encontraron "
            f"{total_turns}."
        )

    # ----------------------------------------------------------
    # INSTANCIAR REGLAS
    # ----------------------------------------------------------

    rules = RestructuringRules()

    stats = {
        code: Counter()
        for code in IR_CODES
    }

    applicable_examples = defaultdict(list)
    na_examples = defaultdict(list)

    anomalies: list[dict[str, Any]] = []

    versions = defaultdict(Counter)

    # ==========================================================
    # FASE 1
    #
    # AUDITORÍA DEL GATE / APLICABILIDAD
    #
    # IMPORTANTE:
    # NO se fabrican respuestas de IA.
    # ==========================================================

    for scenario in scenarios:

        scenario_code = scenario["scenario"]

        for index, turn in enumerate(
            scenario["turns"]
        ):

            turn_number = int(
                turn.get(
                    "id",
                    index + 1,
                )
            )

            user_text = str(
                turn.get(
                    "user",
                    "",
                )
            ).strip()

            # --------------------------------------------------
            # Contexto acumulado real de EvalIA
            # --------------------------------------------------

            context = build_context(
                scenario=scenario,
                current_index=index,
                assistant_text=".",
            )

            # --------------------------------------------------
            # IR1 → IR8
            # --------------------------------------------------

            for code in IR_CODES:

                try:

                    result = evaluate_indicator(
                        rules=rules,
                        indicator_code=code,
                        context=context,
                    )

                    data = result_summary(
                        result
                    )

                except Exception as exc:

                    anomalies.append(
                        {
                            "scenario": scenario_code,
                            "turn": turn_number,
                            "indicator": code,
                            "type": "ERROR",
                            "detail": repr(exc),
                        }
                    )

                    stats[code]["ERROR"] += 1

                    continue

                applicable = data["applicable"]
                score = data["score"]

                # --------------------------------------------------
                # Registrar versión
                # --------------------------------------------------

                version = data["rule_version"]

                if version:
                    versions[code][version] += 1

                # --------------------------------------------------
                # APLICABLE
                # --------------------------------------------------

                if applicable is True:

                    stats[code]["APLICABLE"] += 1

                    if len(
                        applicable_examples[code]
                    ) < 5:

                        applicable_examples[
                            code
                        ].append(
                            (
                                scenario_code,
                                turn_number,
                                user_text,
                                score,
                                data[
                                    "justification"
                                ],
                            )
                        )

                # --------------------------------------------------
                # N/A
                # --------------------------------------------------

                elif applicable is False:

                    stats[code]["N/A"] += 1

                    if len(
                        na_examples[code]
                    ) < 5:

                        na_examples[
                            code
                        ].append(
                            (
                                scenario_code,
                                turn_number,
                                user_text,
                                data[
                                    "justification"
                                ],
                            )
                        )

                # --------------------------------------------------
                # ESTADO INDETERMINADO
                # --------------------------------------------------

                else:

                    stats[
                        code
                    ][
                        "INDETERMINADO"
                    ] += 1

                    anomalies.append(
                        {
                            "scenario": scenario_code,
                            "turn": turn_number,
                            "indicator": code,
                            "type":
                                "APLICABILIDAD_INDETERMINADA",
                            "detail": data,
                        }
                    )

                # ==================================================
                # INVARIANTES TÉCNICAS
                # ==================================================

                # N/A nunca debe tener score numérico.

                if (
                    applicable is False
                    and score is not None
                ):

                    anomalies.append(
                        {
                            "scenario": scenario_code,
                            "turn": turn_number,
                            "indicator": code,
                            "type": "NA_CON_PUNTAJE",
                            "detail": score,
                        }
                    )

                # Indicador aplicable debe tener score 0–3.

                if (
                    applicable is True
                    and score not in (
                        0,
                        1,
                        2,
                        3,
                    )
                ):

                    anomalies.append(
                        {
                            "scenario": scenario_code,
                            "turn": turn_number,
                            "indicator": code,
                            "type": "PUNTAJE_INVALIDO",
                            "detail": score,
                        }
                    )

                # Confianza, si existe, debe estar entre 0 y 1.

                confidence = data[
                    "confidence"
                ]

                if confidence is not None:

                    try:

                        conf_value = float(
                            confidence
                        )

                        if not (
                            0.0
                            <= conf_value
                            <= 1.0
                        ):

                            anomalies.append(
                                {
                                    "scenario":
                                        scenario_code,
                                    "turn":
                                        turn_number,
                                    "indicator":
                                        code,
                                    "type":
                                        "CONFIANZA_FUERA_RANGO",
                                    "detail":
                                        confidence,
                                }
                            )

                    except (
                        TypeError,
                        ValueError,
                    ):

                        anomalies.append(
                            {
                                "scenario":
                                    scenario_code,
                                "turn":
                                    turn_number,
                                "indicator":
                                    code,
                                "type":
                                    "CONFIANZA_INVALIDA",
                                "detail":
                                    confidence,
                            }
                        )

    # ==========================================================
    # RESULTADOS
    # ==========================================================

    print(
        "\n"
        + "=" * 78
    )

    print(
        "1. RESUMEN DE APLICABILIDAD "
        "EN LOS 190 TURNOS"
    )

    print(
        "=" * 78
    )

    print(
        f"\n"
        f"{'IND':<6}"
        f"{'APLICABLE':>12}"
        f"{'N/A':>10}"
        f"{'ERROR':>10}"
        f"{'OTRO':>10}"
    )

    for code in IR_CODES:

        print(
            f"{code:<6}"
            f"{stats[code]['APLICABLE']:>12}"
            f"{stats[code]['N/A']:>10}"
            f"{stats[code]['ERROR']:>10}"
            f"{stats[code]['INDETERMINADO']:>10}"
        )

    # ==========================================================
    # VERSIONES
    # ==========================================================

    print(
        "\n"
        + "=" * 78
    )

    print(
        "2. VERSIONES DE REGLA OBSERVADAS"
    )

    print(
        "=" * 78
    )

    for code in IR_CODES:

        if versions[code]:

            version_text = ", ".join(
                f"{version} ({count})"
                for version, count
                in versions[code].items()
            )

            print(
                f"{code}: {version_text}"
            )

        else:

            print(
                f"{code}: sin versión reportada"
            )

    # ==========================================================
    # EJEMPLOS APLICABLES
    # ==========================================================

    print(
        "\n"
        + "=" * 78
    )

    print(
        "3. MUESTRAS DE TURNOS "
        "MARCADOS COMO APLICABLES"
    )

    print(
        "=" * 78
    )

    for code in IR_CODES:

        print(
            f"\n--- {code} ---"
        )

        examples = (
            applicable_examples[
                code
            ]
        )

        if not examples:

            print(
                "Sin ejemplos aplicables detectados."
            )

            continue

        for (
            scenario_code,
            turn_number,
            text,
            score,
            justification,
        ) in examples:

            print(
                f"\n"
                f"{scenario_code} · "
                f"T{turn_number}"
            )

            print(
                f"Usuario: {text}"
            )

            print(
                f"Score diagnóstico: {score}"
            )

            print(
                f"Justificación: "
                f"{justification}"
            )

    # ==========================================================
    # EJEMPLOS N/A
    # ==========================================================

    print(
        "\n"
        + "=" * 78
    )

    print(
        "4. MUESTRAS DE TURNOS "
        "MARCADOS N/A"
    )

    print(
        "=" * 78
    )

    for code in IR_CODES:

        print(
            f"\n--- {code} ---"
        )

        examples = (
            na_examples[
                code
            ]
        )

        if not examples:

            print(
                "Sin ejemplos N/A detectados."
            )

            continue

        for (
            scenario_code,
            turn_number,
            text,
            justification,
        ) in examples:

            print(
                f"\n"
                f"{scenario_code} · "
                f"T{turn_number}"
            )

            print(
                f"Usuario: {text}"
            )

            print(
                f"Justificación: "
                f"{justification}"
            )

    # ==========================================================
    # ANOMALÍAS
    # ==========================================================

    print(
        "\n"
        + "=" * 78
    )

    print(
        "5. INVARIANTES / "
        "ANOMALÍAS TÉCNICAS"
    )

    print(
        "=" * 78
    )

    if not anomalies:

        print(
            "\n[OK] No se detectaron "
            "anomalías estructurales."
        )

    else:

        print(
            f"\nSe detectaron "
            f"{len(anomalies)} anomalías:"
        )

        for item in anomalies[:50]:

            print(
                f"- "
                f"{item['scenario']} "
                f"T{item['turn']} "
                f"{item['indicator']} · "
                f"{item['type']} · "
                f"{item['detail']}"
            )

        if len(anomalies) > 50:

            print(
                f"... y "
                f"{len(anomalies) - 50} "
                f"anomalías adicionales."
            )

    # ==========================================================
    # INTERPRETACIÓN
    # ==========================================================

    print(
        "\n"
        + "=" * 78
    )

    print(
        "6. INTERPRETACIÓN DEL AUDITOR"
    )

    print(
        "=" * 78
    )

    print(
        """
Este reporte NO determina todavía si IR1–IR8 están científicamente
cerrados.

Esta fase permite:

1. comprobar que los 38 escenarios y 190 turnos pueden procesarse;
2. observar el comportamiento de los gates de aplicabilidad;
3. detectar N/A potencialmente excesivos o insuficientes;
4. verificar el funcionamiento con contexto acumulado;
5. detectar anomalías estructurales;
6. localizar casos semánticos que merecen revisión dirigida;
7. preparar el stress test independiente de la familia IR.

IMPORTANTE:

Las respuestas de IA están vacías deliberadamente.

Por tanto, cualquier score generado en esta auditoría NO representa
la calidad de ChatGPT, Gemini, Claude, Copilot, Perplexity ni ningún
otro modelo.

El banco de escenarios se utiliza aquí como corpus de estrés para
analizar las condiciones del contexto del usuario.

La validación semántica del puntaje 0–3 requiere posteriormente pares
controlados usuario + respuesta IA y, finalmente, comparación con
evaluación humana.
"""
    )

    print(
        "=" * 78
    )

    print(
        "FIN DE AUDITORÍA FAMILIAR IR"
    )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()