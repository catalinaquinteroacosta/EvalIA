from __future__ import annotations

import json
import hashlib
import sqlite3
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.database import get_connection
from backend.evaluators.evaluation_context import EvaluationContext, ConversationTurn
from backend.evaluators.evaluation_runner import EvaluationRunner
from backend.prompt_loader import load_prompt
from backend.pdf_export import build_results_pdf

app = FastAPI(
    title="EvalIA",
    description=(
        "Framework para evaluación de IA conversacional "
        "en contextos emocionales"
    ),
    version="1.0.0",
)


BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


# =========================================================
# MODELOS DE ENTRADA
# =========================================================

class ExperimentRequest(BaseModel):
    scenario_code: str = Field(min_length=1)
    model_names: list[str] = Field(min_length=1)

    category: str | None = None
    custom_turns: list[dict[str, Any]] | None = None


class FreeTurnRequest(BaseModel):
    user_message: str = Field(min_length=1)


class ManualResponseRequest(BaseModel):
    experiment_id: int = Field(gt=0)
    model_name: str = Field(min_length=1)
    turn_number: int = Field(gt=0)
    response_text: str = Field(min_length=1)


app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR),
    name="static",
)


# =========================================================
# UTILIDADES INTERNAS
# =========================================================

def _close_and_raise(
    connection: sqlite3.Connection,
    status_code: int,
    detail: str,
) -> None:
    connection.close()
    raise HTTPException(
        status_code=status_code,
        detail=detail,
    )


def _get_response_context(
    response_id: int,
) -> dict[str, Any]:
    """
    Obtiene la respuesta, su turno, escenario, experimento y modelo.

    Para experimentos LIBRE, la información del escenario y el mensaje
    del usuario se toma del snapshot inmutable del experimento.
    """
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            responses.id AS response_id,
            responses.experiment_id,
            responses.scenario_id,
            responses.turn_id,
            responses.ai_model_id,
            responses.response_text,
            responses.created_at AS response_created_at,
            conversation_turns.turn_number,
            conversation_turns.user_message,
            scenarios.code AS scenario_code,
            scenarios.category AS scenario_category,
            scenarios.title AS scenario_title,
            scenarios.description AS scenario_description,
            scenarios.rubric_type,
            ai_models.name AS model_name,
            ai_models.provider AS model_provider
        FROM responses
        JOIN conversation_turns
            ON responses.turn_id = conversation_turns.id
        JOIN scenarios
            ON responses.scenario_id = scenarios.id
        JOIN ai_models
            ON responses.ai_model_id = ai_models.id
        WHERE responses.id = ?
        """,
        (response_id,),
    )

    row = cursor.fetchone()

    if row is None:
        connection.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Respuesta no encontrada",
        )

    result = dict(row)

    try:
        cursor.execute(
            """
            SELECT scenario_snapshot_json
            FROM experiments
            WHERE id = ?
            """,
            (result["experiment_id"],),
        )
        experiment_row = cursor.fetchone()
    finally:
        connection.close()

    if experiment_row is not None and experiment_row["scenario_snapshot_json"]:
        try:
            snapshot = json.loads(experiment_row["scenario_snapshot_json"])
        except json.JSONDecodeError as error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="El snapshot del experimento contiene un JSON inválido",
            ) from error

        if snapshot.get("scenario") == "LIBRE":
            result["scenario_code"] = "LIBRE"
            result["scenario_category"] = snapshot.get(
                "category",
                result["scenario_category"],
            )
            result["scenario_title"] = snapshot.get(
                "title",
                "Experimento libre",
            )
            result["scenario_description"] = snapshot.get(
                "description",
                "Conversación personalizada para validación del framework de EvalIA.",
            )
            result["rubric_type"] = snapshot.get(
                "rubric_type",
                result["rubric_type"],
            )

        # All versioned experiments use their frozen text, including the
        # official bank; the historical FK retains its original row/text.
        turn_number = int(result["turn_number"])
        for turn in snapshot.get("turns", []):
            if int(turn.get("id", 0)) == turn_number:
                result["user_message"] = turn.get("user", "")
                break

    return result


def _validate_prompt_consistency(
    scenario_code: str,
    scenario_id: int,
) -> None:
    """
    Verifica que el JSON canónico y SQLite describan exactamente los mismos turnos.

    Esta función es deliberadamente de solo lectura: nunca sincroniza ni corrige
    datos durante una operación experimental. Si existe una divergencia, bloquea
    la operación para evitar mostrar un estímulo y evaluar otro diferente.
    """
    normalized_code = scenario_code.strip()
    prompt_data = load_prompt(normalized_code)

    if prompt_data is None:
        raise ValueError(
            f"No existe el archivo JSON canónico del escenario '{normalized_code}'."
        )

    declared_code = prompt_data.get("scenario")
    if declared_code != normalized_code:
        raise ValueError(
            f"El JSON solicitado como '{normalized_code}' declara el escenario "
            f"'{declared_code}'."
        )

    json_turns = prompt_data.get("turns")
    if not isinstance(json_turns, list) or not json_turns:
        raise ValueError(
            f"El escenario '{normalized_code}' no contiene turnos válidos "
            "en su JSON canónico."
        )

    canonical_turns: list[tuple[int, str]] = []
    seen_turn_numbers: set[int] = set()

    for position, turn in enumerate(json_turns, start=1):
        if not isinstance(turn, dict):
            raise ValueError(
                f"Turno inválido en el JSON de '{normalized_code}', "
                f"posición {position}."
            )

        turn_number = turn.get("id")
        user_message = turn.get("user")

        if not isinstance(turn_number, int) or turn_number <= 0:
            raise ValueError(
                f"ID de turno inválido en '{normalized_code}', "
                f"posición {position}."
            )

        if turn_number in seen_turn_numbers:
            raise ValueError(
                f"El escenario '{normalized_code}' repite el turno {turn_number}."
            )

        if not isinstance(user_message, str) or not user_message.strip():
            raise ValueError(
                f"Mensaje de usuario inválido en '{normalized_code}', "
                f"turno {turn_number}."
            )

        seen_turn_numbers.add(turn_number)
        canonical_turns.append((turn_number, user_message.strip()))

    canonical_turns.sort(key=lambda item: item[0])
    expected_numbers = list(range(1, len(canonical_turns) + 1))
    actual_numbers = [turn_number for turn_number, _ in canonical_turns]

    if actual_numbers != expected_numbers:
        raise ValueError(
            f"Los turnos de '{normalized_code}' deben ser consecutivos desde 1. "
            f"Encontrados: {actual_numbers}."
        )

    if prompt_data.get("bank_version"):
        # load_prompt has verified the immutable versioned manifest and every
        # requested prompt. Legacy conversation_turns remain historical FKs;
        # their text must not be overwritten when a new bank is approved.
        if actual_numbers != [1, 2, 3, 4, 5]:
            raise ValueError("El banco oficial debe contener cinco turnos.")
        connection = get_connection()
        try:
            scenario = connection.execute(
                "SELECT code, category, rubric_type FROM scenarios WHERE id=?", (scenario_id,)
            ).fetchone()
            if scenario is None or scenario["code"] != normalized_code or scenario["category"] != prompt_data["category"] or scenario["rubric_type"] != prompt_data["rubric_type"]:
                raise ValueError("Metadatos del banco oficial no coinciden con el escenario.")
        finally:
            connection.close()
        return

    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT turn_number, user_message
            FROM conversation_turns
            WHERE scenario_id = ?
            ORDER BY turn_number
            """,
            (scenario_id,),
        )
        database_turns = [
            (int(row["turn_number"]), row["user_message"].strip())
            for row in cursor.fetchall()
        ]
    finally:
        connection.close()

    if canonical_turns != database_turns:
        raise ValueError(
            f"Inconsistencia detectada en el escenario '{normalized_code}': "
            "los turnos del JSON canónico no coinciden con conversation_turns "
            "en SQLite. Ejecuta backend/seed_turns.py y verifica el cambio "
            "antes de continuar."
        )


def _require_prompt_consistency(
    scenario_code: str,
    scenario_id: int,
) -> None:
    """Convierte un fallo de consistencia en una respuesta HTTP explícita."""
    try:
        _validate_prompt_consistency(scenario_code, scenario_id)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error


def _canonical_scenario_snapshot(scenario_code: str, scenario_id: int) -> tuple[dict[str, Any], str]:
    """Construye el snapshot canónico actual y su huella SHA-256."""
    _validate_prompt_consistency(scenario_code, scenario_id)
    prompt_data = load_prompt(scenario_code)
    if prompt_data is None:
        raise ValueError(f"No existe el JSON canónico de '{scenario_code}'.")
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT category, title, rubric_type FROM scenarios WHERE id = ? AND code = ?", (scenario_id, scenario_code))
        scenario = cursor.fetchone()
        if scenario is None:
            raise ValueError(f"Escenario '{scenario_code}' no encontrado en SQLite.")
    finally:
        connection.close()
    snapshot = {
        "scenario": scenario_code,
        "title": scenario["title"],
        "category": scenario["category"],
        "rubric_type": scenario["rubric_type"],
        "turns": [{"id": int(t["id"]), "user": t["user"] if prompt_data.get("bank_version") else t["user"].strip()} for t in prompt_data["turns"]],
    }
    if prompt_data.get("bank_version"):
        snapshot["bank_version"] = prompt_data["bank_version"]
        snapshot["source_sha256"] = prompt_data["source_sha256"]
    serialized = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return snapshot, hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _load_experiment_snapshot(experiment_id: int) -> dict[str, Any]:
    """Carga el estímulo inmutable guardado al crear el experimento."""
    connection = get_connection(); cursor = connection.cursor()
    try:
        cursor.execute("SELECT scenario_snapshot_json FROM experiments WHERE id = ?", (experiment_id,))
        row = cursor.fetchone()
    finally:
        connection.close()
    if row is None:
        raise ValueError(f"Experimento {experiment_id} no encontrado.")
    if not row["scenario_snapshot_json"]:
        raise ValueError(
            f"El experimento {experiment_id} es histórico y no posee snapshot verificable del escenario. "
            "No se evaluará automáticamente hasta validar explícitamente su estímulo histórico."
        )
    try:
        return json.loads(row["scenario_snapshot_json"])
    except json.JSONDecodeError as error:
        raise ValueError(f"El snapshot del experimento {experiment_id} está corrupto.") from error


def _read_experiment_snapshot(experiment_id: int) -> dict[str, Any]:
    """Read stored history without certifying it for new evaluation or edits."""
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT scenario_snapshot_json, scenario_id FROM experiments WHERE id=?",
            (experiment_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Experimento no encontrado")
        if row["scenario_snapshot_json"]:
            snapshot = json.loads(row["scenario_snapshot_json"])
            if not isinstance(snapshot, dict) or not isinstance(snapshot.get("turns"), list):
                raise ValueError("Snapshot histórico inválido")
            return snapshot
        turns = connection.execute(
            "SELECT turn_number, user_message FROM conversation_turns WHERE scenario_id=? ORDER BY turn_number",
            (row["scenario_id"],),
        ).fetchall()
        return {"turns": [{"id": t["turn_number"], "user": t["user_message"]} for t in turns],
                "historical_read_only": True}
    finally:
        connection.close()


def _require_experiment_snapshot_current(
    experiment_id: int,
    scenario_code: str,
    scenario_id: int,
) -> dict[str, Any]:
    """
    Impide mezclar versiones de un escenario dentro del mismo experimento.

    Los experimentos LIBRE utilizan exclusivamente su snapshot inmutable
    y no dependen de un JSON canónico.
    """
    snapshot = _load_experiment_snapshot(experiment_id)

    if snapshot.get("scenario") == "LIBRE":
        return snapshot

    current_snapshot, current_hash = _canonical_scenario_snapshot(
        scenario_code,
        scenario_id,
    )

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "SELECT scenario_hash FROM experiments WHERE id = ?",
            (experiment_id,),
        )
        row = cursor.fetchone()
    finally:
        connection.close()

    stored_hash = row["scenario_hash"] if row else None

    if (
        not stored_hash
        or stored_hash != current_hash
        or snapshot != current_snapshot
    ):
        raise ValueError(
            f"El escenario '{scenario_code}' cambió después de crear "
            f"el experimento {experiment_id}. EvalIA bloqueó la operación "
            "para no mezclar versiones. Crea un experimento nuevo."
        )

    return snapshot


def _normalize_engine_rubric_type(rubric_type: str) -> str:
    """
    Traduce la clasificación de negocio guardada en SQLite al nombre
    técnico esperado por el motor determinístico.

    - trastorno -> ansiedad_depresion
    - crisis    -> crisis
    """
    normalized = rubric_type.strip().lower()

    aliases = {
        "trastorno": "ansiedad_depresion",
        "ansiedad_depresion": "ansiedad_depresion",
        "crisis": "crisis",
    }

    if normalized not in aliases:
        raise ValueError(
            "Tipo de rúbrica no reconocido para el motor: "
            f"'{rubric_type}'."
        )

    return aliases[normalized]

def _rubric_type_from_category(category: str) -> str:
    """
    Determina la rúbrica técnica para un experimento LIBRE
    a partir de la categoría seleccionada en el frontend.

    Ansiedad y Depresión:
        -> rúbrica ansiedad/depresión

    Crisis de pareja, existencial y social:
        -> rúbrica de crisis
    """

    normalized = (
        category
        .strip()
        .lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
    )

    # -----------------------------------------
    # RÚBRICA ANSIEDAD / DEPRESIÓN
    # -----------------------------------------
    if normalized in {
        "ansiedad",
        "depresion",
    }:
        return "trastorno"

    # -----------------------------------------
    # RÚBRICA DE CRISIS
    # -----------------------------------------
    if normalized in {
        "pareja",
        "crisis de pareja",
        "existencial",
        "crisis existencial",
        "social",
        "crisis social",
    }:
        return "crisis"

    raise ValueError(
        f"Categoría no válida para experimento LIBRE: '{category}'."
    )


def _build_free_experiment_snapshot(
    category: str,
    custom_turns: list[dict[str, Any]],
) -> tuple[dict[str, Any], str]:
    """
    Construye el snapshot inmutable de un experimento LIBRE.
    """

    category = category.strip()

    if not category:
        raise ValueError(
            "La categoría es obligatoria para un experimento LIBRE."
        )

    if custom_turns is None:
        custom_turns = []

    if len(custom_turns) > 10:
        raise ValueError(
            "Un experimento LIBRE puede contener máximo 10 turnos."
        )

    rubric_type = _rubric_type_from_category(category)

    normalized_turns = []

    for index, turn in enumerate(custom_turns, start=1):
        if not isinstance(turn, dict):
            raise ValueError(
                f"El turno {index} no tiene un formato válido."
            )

        user_message = str(
            turn.get("user", "")
        ).strip()

        if not user_message:
            raise ValueError(
                f"El turno {index} no puede estar vacío."
            )

        normalized_turns.append({
            "id": index,
            "user": user_message,
        })

    snapshot = {
        "scenario": "LIBRE",
        "title": "Experimento libre",
        "category": category,
        "description": (
            "Conversación personalizada para validación "
            "del framework de EvalIA."
        ),
        "rubric_type": rubric_type,
        "turns": normalized_turns,
    }

    serialized = json.dumps(
        snapshot,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    return (
        snapshot,
        hashlib.sha256(
            serialized.encode("utf-8")
        ).hexdigest(),
    )

def _build_evaluation_context(response_context: dict[str, Any]) -> EvaluationContext:
    """Reconstruye la conversación usando el snapshot inmutable del experimento."""
    snapshot = _load_experiment_snapshot(int(response_context["experiment_id"]))
    connection = get_connection(); cursor = connection.cursor()
    cursor.execute(
        """
        SELECT conversation_turns.turn_number, responses.response_text
        FROM responses
        JOIN conversation_turns ON responses.turn_id = conversation_turns.id
        WHERE responses.experiment_id = ? AND responses.ai_model_id = ?
          AND conversation_turns.turn_number <= ?
        ORDER BY conversation_turns.turn_number
        """,
        (response_context["experiment_id"], response_context["ai_model_id"], response_context["turn_number"]),
    )
    response_by_turn = {int(row["turn_number"]): row["response_text"] for row in cursor.fetchall()}
    connection.close()
    turns = []
    for prompt_turn in snapshot["turns"]:
        number = int(prompt_turn["id"])
        if number > int(response_context["turn_number"]):
            break
        if number in response_by_turn:
            turns.append(ConversationTurn(turn_number=number, user_message=prompt_turn["user"], ai_response=response_by_turn[number]))
    return EvaluationContext(
        experiment_id=int(response_context["experiment_id"]),
        scenario_code=response_context["scenario_code"],
        rubric_type=_normalize_engine_rubric_type(response_context["rubric_type"]),
        model_name=response_context["model_name"],
        turns=turns,
    )


def _public_turn_result(
    runner: EvaluationRunner,
    engine_result: dict[str, Any],
    turn_number: int,
) -> dict[str, Any]:
    return runner.presenter.present_turn(
        turn_number=turn_number,
        evaluation_result=engine_result,
    )


def _public_conversation_result(
    runner: EvaluationRunner,
    engine_result: dict[str, Any],
) -> dict[str, Any]:
    return runner.presenter.present_evaluation(
        evaluation_result=engine_result
    )


def _save_evaluation_result(
    response_id: int,
    internal_result: dict[str, Any],
    public_result: dict[str, Any],
    *, preserve_existing: bool = False,
) -> int:
    """Guarda turno: JSON público en evaluations y detalle técnico en tablas internas."""
    result = internal_result["evaluation"]
    global_result = result["global_result"]
    coverage = global_result["coverage"]
    audit_by_code = {
        item["indicator_code"]: item
        for item in internal_result["indicator_results"]
    }

    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "SELECT id FROM evaluations WHERE response_id = ?",
            (response_id,),
        )
        existing = cursor.fetchone()

        if existing and preserve_existing:
            raise HTTPException(status_code=409, detail="La respuesta ya tiene una evaluación guardada; se conserva intacta.")

        common = (
            result["rubric_type"],
            result["rubric_name"],
            result["rubric_version"],
            public_result.get("engine_version", "deterministic_rules"),
            None,
            global_result["percentage"],
            global_result["classification"],
            global_result["classification_before_critical_rules"],
            global_result["applicable_indicators"],
            global_result["not_applicable_indicators"],
            global_result["total_indicators"],
            coverage["percentage"],
            coverage["label"],
            result["executive_summary"],
            json.dumps(public_result, ensure_ascii=False),
        )

        if existing:
            evaluation_id = int(existing["id"])
            cursor.execute(
                """
                UPDATE evaluations
                SET rubric_type=?, rubric_name=?, rubric_version=?,
                    evaluator_type=?, evaluator_model=?,
                    global_percentage=?, classification=?,
                    classification_before_critical_rules=?,
                    applicable_indicators=?, not_applicable_indicators=?,
                    total_indicators=?, coverage_percentage=?,
                    coverage_label=?, executive_summary=?, result_json=?,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (*common, evaluation_id),
            )
            for table in (
                "evaluation_criteria", "evaluation_indicators",
                "evaluation_strengths", "evaluation_improvements",
                "evaluation_alerts",
            ):
                cursor.execute(
                    f"DELETE FROM {table} WHERE evaluation_id = ?",
                    (evaluation_id,),
                )
        else:
            cursor.execute(
                """
                INSERT INTO evaluations (
                    response_id, rubric_type, rubric_name, rubric_version,
                    evaluator_type, evaluator_model, global_percentage,
                    classification, classification_before_critical_rules,
                    applicable_indicators, not_applicable_indicators,
                    total_indicators, coverage_percentage, coverage_label,
                    executive_summary, result_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (response_id, *common),
            )
            evaluation_id = int(cursor.lastrowid)

        for criterion in result["criteria"]:
            cov = criterion["coverage"]
            cursor.execute(
                """
                INSERT INTO evaluation_criteria (
                    evaluation_id, criterion_code, criterion_name,
                    criterion_order, score_0_to_3, percentage, classification,
                    total_score, maximum_score, applicable_indicators,
                    not_applicable_indicators, total_indicators,
                    coverage_percentage, coverage_label,
                    has_critical_failure, critical_failure_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evaluation_id, criterion["criterion_code"],
                    criterion["criterion_name"], criterion["order"],
                    criterion["score_0_to_3"], criterion["percentage"],
                    criterion["classification"], criterion["total_score"],
                    criterion["maximum_score"], criterion["applicable_indicators"],
                    criterion["not_applicable_indicators"],
                    criterion["total_indicators"], cov["percentage"], cov["label"],
                    int(criterion["has_critical_failure"]),
                    criterion["critical_failure_count"],
                ),
            )

        for indicator in result["internal_detail"]["indicators"]:
            audit = audit_by_code.get(indicator["indicator_code"], {})
            cursor.execute(
                """
                INSERT INTO evaluation_indicators (
                    evaluation_id, criterion_code, indicator_code,
                    applicable, score, justification, indicator_type,
                    criticality, priority, critical_failure
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evaluation_id, indicator["criterion_code"],
                    indicator["indicator_code"], int(indicator["applicable"]),
                    indicator["score"],
                    audit.get("justification", indicator["justification"]),
                    indicator["type"], indicator["criticality"],
                    indicator["priority"], int(indicator["critical_failure"]),
                ),
            )

        for position, value in enumerate(result["strengths"], 1):
            cursor.execute(
                "INSERT INTO evaluation_strengths (evaluation_id, position, text) VALUES (?, ?, ?)",
                (evaluation_id, position, value),
            )
        for position, value in enumerate(result["improvement_opportunities"], 1):
            cursor.execute(
                "INSERT INTO evaluation_improvements (evaluation_id, position, text) VALUES (?, ?, ?)",
                (evaluation_id, position, value),
            )
        for alert in result["critical_alerts"]:
            cursor.execute(
                """
                INSERT INTO evaluation_alerts (
                    evaluation_id, indicator_code, criterion_code,
                    criterion_name, priority, score, message
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evaluation_id, alert["indicator_code"],
                    alert["criterion_code"], alert["criterion_name"],
                    alert["priority"], alert["score"], alert["message"],
                ),
            )

        connection.commit()
        return evaluation_id
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _save_conversation_evaluation(
    context: EvaluationContext,
    ai_model_id: int,
    internal_result: dict[str, Any],
    public_result: dict[str, Any],
) -> int:
    """Guarda la evaluación longitudinal separada del resultado de cada turno."""
    result = internal_result["evaluation"]
    global_result = result["global_result"]
    coverage = global_result["coverage"]
    internal_json = json.dumps(internal_result, ensure_ascii=False)
    public_json = json.dumps(public_result, ensure_ascii=False)

    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT id FROM conversation_evaluations
            WHERE experiment_id=? AND ai_model_id=?
            """,
            (context.experiment_id, ai_model_id),
        )
        existing = cursor.fetchone()

        values = (
            context.rubric_type, result["rubric_name"], result["rubric_version"],
            "deterministic_rules", global_result["percentage"],
            global_result["classification"],
            global_result["classification_before_critical_rules"],
            global_result["applicable_indicators"],
            global_result["not_applicable_indicators"],
            global_result["total_indicators"], coverage["percentage"],
            coverage["label"], result["executive_summary"],
            internal_json, public_json,
        )

        if existing:
            evaluation_id = int(existing["id"])
            cursor.execute(
                """
                UPDATE conversation_evaluations
                SET rubric_type=?, rubric_name=?, rubric_version=?,
                    evaluator_type=?, global_percentage=?, classification=?,
                    classification_before_critical_rules=?,
                    applicable_indicators=?, not_applicable_indicators=?,
                    total_indicators=?, coverage_percentage=?, coverage_label=?,
                    executive_summary=?, internal_result_json=?,
                    public_result_json=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (*values, evaluation_id),
            )
        else:
            cursor.execute(
                """
                INSERT INTO conversation_evaluations (
                    experiment_id, ai_model_id, rubric_type, rubric_name,
                    rubric_version, evaluator_type, global_percentage,
                    classification, classification_before_critical_rules,
                    applicable_indicators, not_applicable_indicators,
                    total_indicators, coverage_percentage, coverage_label,
                    executive_summary, internal_result_json, public_result_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (context.experiment_id, ai_model_id, *values),
            )
            evaluation_id = int(cursor.lastrowid)

        # -------------------------------------------------------------
        # Recalcula el estado global del experimento.
        #
        # Un experimento solo queda "completed" cuando:
        #   1) todos los modelos seleccionados tienen respuesta para
        #      todos los turnos del snapshot;
        #   2) todas esas respuestas tienen evaluación individual; y
        #   3) cada modelo seleccionado tiene evaluación longitudinal.
        #
        # Si una respuesta se edita, save_manual_response invalida su
        # evaluación y la longitudinal del modelo y vuelve a dejar el
        # experimento en "in_progress".
        # -------------------------------------------------------------
        cursor.execute(
            """
            SELECT scenario_snapshot_json
            FROM experiments
            WHERE id = ?
            """,
            (context.experiment_id,),
        )
        experiment_row = cursor.fetchone()

        if experiment_row is None:
            raise ValueError(
                f"No existe el experimento {context.experiment_id}."
            )

        snapshot_raw = experiment_row["scenario_snapshot_json"]
        if not snapshot_raw:
            # Compatibilidad con experimentos históricos creados antes
            # de incorporar snapshots: no se marcan automáticamente
            # como completed porque no puede probarse el número exacto
            # de estímulos congelados.
            expected_turns = None
        else:
            snapshot = json.loads(snapshot_raw)
            snapshot_turns = snapshot.get("turns")
            if not isinstance(snapshot_turns, list) or not snapshot_turns:
                raise ValueError(
                    "El snapshot del experimento no contiene turnos válidos."
                )
            expected_turns = len(snapshot_turns)

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM experiment_models
            WHERE experiment_id = ?
            """,
            (context.experiment_id,),
        )
        expected_models = int(cursor.fetchone()["total"])

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM responses
            WHERE experiment_id = ?
            """,
            (context.experiment_id,),
        )
        saved_responses = int(cursor.fetchone()["total"])

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM evaluations
            JOIN responses
              ON responses.id = evaluations.response_id
            WHERE responses.experiment_id = ?
            """,
            (context.experiment_id,),
        )
        saved_turn_evaluations = int(cursor.fetchone()["total"])

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM conversation_evaluations
            WHERE experiment_id = ?
            """,
            (context.experiment_id,),
        )
        saved_conversation_evaluations = int(cursor.fetchone()["total"])

        expected_responses = (
            expected_models * expected_turns
            if expected_turns is not None
            else None
        )

        is_complete = (
            expected_responses is not None
            and expected_models > 0
            and saved_responses == expected_responses
            and saved_turn_evaluations == expected_responses
            and saved_conversation_evaluations == expected_models
        )

        cursor.execute(
            """
            UPDATE experiments
            SET status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                "completed" if is_complete else "in_progress",
                context.experiment_id,
            ),
        )

        connection.commit()
        return evaluation_id
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

def _load_evaluation_indicators(
    evaluation_id: int,
) -> list[dict[str, Any]]:
    """
    Carga la trazabilidad técnica de indicadores de una evaluación.

    Esta información complementa el resultado público sin modificarlo.
    Permite auditar, por indicador, aplicabilidad, puntuación,
    justificación, tipo, criticidad, prioridad y fallas críticas.
    """
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                criterion_code,
                indicator_code,
                applicable,
                score,
                justification,
                indicator_type,
                criticality,
                priority,
                critical_failure
            FROM evaluation_indicators
            WHERE evaluation_id = ?
            ORDER BY id
            """,
            (evaluation_id,),
        )

        rows = cursor.fetchall()

        return [
            {
                "criterion_code": row["criterion_code"],
                "indicator_code": row["indicator_code"],
                "applicable": bool(row["applicable"]),
                "score": row["score"],
                "justification": row["justification"],
                "indicator_type": row["indicator_type"],
                "criticality": row["criticality"],
                "priority": row["priority"],
                "critical_failure": bool(row["critical_failure"]),
            }
            for row in rows
        ]

    finally:
        connection.close()

def _load_saved_evaluation(response_id: int) -> dict[str, Any]:
    """Carga únicamente el JSON público almacenado para el turno."""
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT evaluations.id, evaluations.response_id,
               evaluations.evaluator_type, evaluations.created_at,
               evaluations.updated_at, evaluations.result_json,
               ai_models.name AS evaluated_model,
               ai_models.provider AS evaluated_provider,
               conversation_turns.turn_number,
               scenarios.code AS scenario_code,
               scenarios.title AS scenario_title
        FROM evaluations
        JOIN responses ON evaluations.response_id=responses.id
        JOIN ai_models ON responses.ai_model_id=ai_models.id
        JOIN conversation_turns ON responses.turn_id=conversation_turns.id
        JOIN scenarios ON responses.scenario_id=scenarios.id
        WHERE evaluations.response_id=?
        """,
        (response_id,),
    )
    row = cursor.fetchone()
    connection.close()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La respuesta todavía no tiene una evaluación",
        )
    try:
        result = json.loads(row["result_json"])
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="La evaluación guardada contiene un JSON inválido",
        ) from error

    return {
        "evaluation_id": row["id"], "response_id": row["response_id"],
        "evaluator_type": row["evaluator_type"],
        "evaluated_model": row["evaluated_model"],
        "evaluated_provider": row["evaluated_provider"],
        "scenario_code": row["scenario_code"],
        "scenario_title": row["scenario_title"],
        "turn_number": row["turn_number"],
        "created_at": row["created_at"], "updated_at": row["updated_at"],
        "result": result,
    }


# =========================================================
# PÁGINAS DEL FRONTEND
# =========================================================

@app.get("/")
def home():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/nuevo-experimento")
def nuevo_experimento():
    return FileResponse(
        FRONTEND_DIR / "nuevo_experimento.html"
    )


@app.get("/laboratorio")
def laboratorio():
    return FileResponse(FRONTEND_DIR / "laboratorio.html")


@app.get("/experimentos")
def experiment_history_page():
    return FileResponse(FRONTEND_DIR / "experimentos.html")


@app.get("/configuracion")
def configuration_page():
    return FileResponse(FRONTEND_DIR / "configuracion.html")


@app.get("/resultados")
def resultados():
    return FileResponse(FRONTEND_DIR / "resultados.html")


# =========================================================
# ESTADO DEL SISTEMA
# =========================================================

@app.get("/api/status")
def system_status():
    dependencies = getattr(app.state, 'evaluation_dependencies', None) or {}
    configured = bool(dependencies.get('crisis_provider') and dependencies.get('anxiety_reader'))
    replay_only = dependencies.get('replay_only') is True
    return {
        "project": "EvalIA",
        "status": "Activo",
        "mode": "validated_semantic_v2",
        "crisis_engine": "CRISIS-ADENDA-V11-VERIFIED-20261014-1",
        "anxiety_engine": "ANXIETY-ISOLATION-CANDIDATE-20261014-1",
        "message": ("Consulta sin gasto y modo REAL de GPT-6 Luna disponible con confirmación desde el laboratorio." if replay_only else
                    "Lector semántico configurado con alcance autorizado." if configured else
                    "Captura manual disponible; evaluación API deshabilitada hasta configurar autorización y presupuesto."),
        "semantic_reader_configured": configured,
        "replay_only": replay_only,
        "paid_execution_enabled": configured and not replay_only and dependencies.get('paid_submission_enabled') is True,
        "generation_mode": "manual_capture",
        "generation_api_configured": False,
        "real_mode_available": True,
        "real_confirmation_required": True,
        "real_evaluator_model": "gpt-6-luna",
        "models": [{"name": name, "input_mode": "manual_capture", "api_model_id": None}
                   for name in ("ChatGPT", "Gemini", "Claude", "Copilot", "Perplexity")],
    }


# =========================================================
# ESCENARIOS DESDE SQLITE
# =========================================================

@app.get("/api/scenarios/{scenario_code}")
def get_scenario(scenario_code: str):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            code,
            category,
            title,
            description,
            rubric_type
        FROM scenarios
        WHERE code = ?
          AND active = 1
        """,
        (scenario_code.strip(),),
    )

    scenario = cursor.fetchone()

    if scenario is None:
        _close_and_raise(
            connection,
            status.HTTP_404_NOT_FOUND,
            "Escenario no encontrado",
        )

    try:
        _validate_prompt_consistency(scenario["code"], int(scenario["id"]))
    except ValueError as error:
        _close_and_raise(
            connection,
            status.HTTP_409_CONFLICT,
            str(error),
        )

    cursor.execute(
        """
        SELECT
            id,
            turn_number,
            user_message
        FROM conversation_turns
        WHERE scenario_id = ?
        ORDER BY turn_number
        """,
        (scenario["id"],),
    )

    turns = cursor.fetchall()
    connection.close()

    current_prompt = load_prompt(scenario["code"])
    if current_prompt and current_prompt.get("bank_version"):
        official_by_number = {int(t["id"]): t["user"] for t in current_prompt["turns"]}
        turns = [dict(t, user_message=official_by_number[int(t["turn_number"])]) for t in turns]

    return {
        "id": scenario["id"],
        "code": scenario["code"],
        "category": scenario["category"],
        "title": scenario["title"],
        "description": scenario["description"],
        "rubric_type": scenario["rubric_type"],
        "turns": [
            {
                "id": turn["id"],
                "turn_number": turn["turn_number"],
                "user_message": turn["user_message"],
            }
            for turn in turns
        ],
    }


# =========================================================
# CREAR EXPERIMENTO
# =========================================================

@app.post(
    "/api/experiments",
    status_code=status.HTTP_201_CREATED,
)
def create_experiment(request: ExperimentRequest):
    scenario_code = request.scenario_code.strip()
    model_names = [
        name.strip()
        for name in request.model_names
        if name.strip()
    ]

    model_names = list(dict.fromkeys(model_names))

    is_free_experiment = scenario_code.upper() == "LIBRE"

    if not model_names:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Debes seleccionar al menos un modelo",
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:
        if is_free_experiment:
            if not request.category:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "Debes seleccionar una categoría para "
                        "el experimento LIBRE."
                    ),
                )

            try:
                rubric_type = _rubric_type_from_category(
                    request.category
                )
                scenario_snapshot, scenario_hash = (
                    _build_free_experiment_snapshot(
                        request.category,
                        request.custom_turns,
                    )
                )
            except ValueError as error:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=str(error),
                ) from error

            # LIBRE usa un escenario técnico existente únicamente para
            # satisfacer la relación de la base de datos. El estímulo real
            # del experimento queda congelado en scenario_snapshot_json.
            cursor.execute(
                """
                SELECT id
                FROM scenarios
                WHERE rubric_type = ?
                  AND active = 1
                ORDER BY id
                LIMIT 1
                """,
                (rubric_type,),
            )

            scenario = cursor.fetchone()

            if scenario is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=(
                        "No existe un escenario técnico disponible "
                        "para la rúbrica seleccionada."
                    ),
                )

        else:
            cursor.execute(
                """
                SELECT id
                FROM scenarios
                WHERE code = ?
                  AND active = 1
                """,
                (scenario_code,),
            )

            scenario = cursor.fetchone()

            if scenario is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Escenario no encontrado",
                )

            _require_prompt_consistency(
                scenario_code=scenario_code,
                scenario_id=int(scenario["id"]),
            )

            try:
                scenario_snapshot, scenario_hash = (
                    _canonical_scenario_snapshot(
                        scenario_code,
                        int(scenario["id"]),
                    )
                )
            except ValueError as error:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=str(error),
                ) from error

        placeholders = ", ".join(
            "?" for _ in model_names
        )

        cursor.execute(
            f"""
            SELECT id, name
            FROM ai_models
            WHERE name IN ({placeholders})
              AND active = 1
            """,
            tuple(model_names),
        )

        model_rows = cursor.fetchall()
        found_names = {
            row["name"]
            for row in model_rows
        }
        missing_names = [
            name
            for name in model_names
            if name not in found_names
        ]

        if missing_names:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Modelos no encontrados o inactivos: "
                    + ", ".join(missing_names)
                ),
            )

        cursor.execute(
            """
            INSERT INTO experiments (
                scenario_id,
                status,
                scenario_snapshot_json,
                scenario_hash
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                scenario["id"],
                "created",
                json.dumps(
                    scenario_snapshot,
                    ensure_ascii=False,
                ),
                scenario_hash,
            ),
        )

        experiment_id = cursor.lastrowid

        # LIBRE obtiene un escenario técnico exclusivo por experimento.
        # Esto evita mezclar los turnos personalizados con los escenarios
        # canónicos y permite agregar hasta 10 turnos de forma progresiva.
        if is_free_experiment:
            free_scenario_code = f"LIBRE-{experiment_id}"
            cursor.execute(
                """
                INSERT INTO scenarios (
                    code, category, title, description, rubric_type, active
                )
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (
                    free_scenario_code,
                    request.category.strip(),
                    "Experimento libre",
                    "Conversación personalizada para validación del framework de EvalIA.",
                    rubric_type,
                ),
            )
            free_scenario_id = cursor.lastrowid
            cursor.execute(
                "UPDATE experiments SET scenario_id = ? WHERE id = ?",
                (free_scenario_id, experiment_id),
            )
            scenario_id_for_experiment = free_scenario_id
        else:
            scenario_id_for_experiment = scenario["id"]

        model_id_by_name = {
            row["name"]: row["id"]
            for row in model_rows
        }

        for model_name in model_names:
            cursor.execute(
                """
                INSERT INTO experiment_models (
                    experiment_id,
                    ai_model_id
                )
                VALUES (?, ?)
                """,
                (
                    experiment_id,
                    model_id_by_name[model_name],
                ),
            )

        connection.commit()

    except HTTPException:
        connection.rollback()
        raise

    except Exception as error:
        connection.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible crear el experimento",
        ) from error

    finally:
        connection.close()

    return {
        "experiment_id": experiment_id,
        "scenario_code": "LIBRE" if is_free_experiment else scenario_code,
        "category": (
            request.category
            if is_free_experiment
            else None
        ),
        "models": model_names,
        "status": "created",
    }


# =========================================================
# CONSULTAR EXPERIMENTO
# =========================================================
# CONSULTAR EXPERIMENTO
# =========================================================

@app.get("/api/experiments/{experiment_id}")
def get_experiment(experiment_id: int):
    archive=getattr(app.state,'published_results',None)
    if archive and experiment_id in archive.experiment_ids:
        return archive.experiment(experiment_id)['details']
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            experiments.id,
            experiments.status,
            experiments.created_at,
            experiments.updated_at,
            scenarios.id AS scenario_id,
            scenarios.code,
            scenarios.category,
            scenarios.title,
            scenarios.description,
            scenarios.rubric_type
        FROM experiments
        JOIN scenarios
            ON experiments.scenario_id = scenarios.id
        WHERE experiments.id = ?
        """,
        (experiment_id,),
    )

    experiment = cursor.fetchone()

    if experiment is None:
        _close_and_raise(
            connection,
            status.HTTP_404_NOT_FOUND,
            "Experimento no encontrado",
        )

    snapshot = _read_experiment_snapshot(experiment_id)

    cursor.execute(
        """
        SELECT id, turn_number
        FROM conversation_turns
        WHERE scenario_id = ?
        ORDER BY turn_number
        """,
        (experiment["scenario_id"],),
    )
    turn_ids = {
        int(row["turn_number"]): int(row["id"])
        for row in cursor.fetchall()
    }

    is_free = snapshot.get("scenario") == "LIBRE"

    turns = [
        {
            "id": turn_ids.get(int(turn["id"])),
            "turn_number": int(turn["id"]),
            "user_message": turn["user"],
        }
        for turn in snapshot["turns"]
    ]

    cursor.execute(
        """
        SELECT
            ai_models.id,
            ai_models.name,
            ai_models.provider
        FROM experiment_models
        JOIN ai_models
            ON experiment_models.ai_model_id = ai_models.id
        WHERE experiment_models.experiment_id = ?
        ORDER BY ai_models.name
        """,
        (experiment_id,),
    )

    models = cursor.fetchall()
    if not models:
        models = cursor.execute(
            "SELECT DISTINCT ai_models.id, ai_models.name, ai_models.provider FROM responses JOIN ai_models ON responses.ai_model_id=ai_models.id WHERE responses.experiment_id=? ORDER BY ai_models.name",
            (experiment_id,),
        ).fetchall()
    connection.close()

    scenario_code = "LIBRE" if is_free else experiment["code"]
    category = snapshot.get("category", experiment["category"]) if is_free else experiment["category"]
    title = snapshot.get("title", experiment["title"]) if is_free else experiment["title"]
    description = snapshot.get("description", experiment["description"]) if is_free else experiment["description"]
    rubric_type = snapshot.get("rubric_type", experiment["rubric_type"]) if is_free else experiment["rubric_type"]

    return {
        "id": experiment["id"],
        "status": experiment["status"],
        "created_at": experiment["created_at"],
        "updated_at": experiment["updated_at"],
        "historical_read_only": bool(snapshot.get("historical_read_only")),
        "scenario": {
            "id": experiment["scenario_id"],
            "code": scenario_code,
            "category": category,
            "title": title,
            "description": description,
            "rubric_type": rubric_type,
            "turns": [
                {
                    "id": turn["id"],
                    "turn_number": turn["turn_number"],
                    "user_message": turn["user_message"],
                }
                for turn in turns
            ],
        },
        "models": [
            {
                "id": model["id"],
                "name": model["name"],
                "provider": model["provider"],
            }
            for model in models
        ],
    }


@app.get("/api/experiments")
def list_experiments(limit: int = 50, offset: int = 0):
    if limit < 1 or limit > 200 or offset < 0:
        raise HTTPException(status_code=422, detail="Paginación inválida")
    connection = get_connection()
    try:
        archive=getattr(app.state,'published_results',None)
        if archive:
            items=[*archive.catalog()['experiments'],*[dict(r) for r in connection.execute(
                'SELECT e.id,e.status,s.code AS scenario_code,s.rubric_type FROM experiments e JOIN scenarios s ON s.id=e.scenario_id')]]
            items=[dict(r,scenario_code=r.get('scenario_code',r.get('code'))) for r in items]
            items.sort(key=lambda r:r['id'])
            return dict(total=len(items),limit=limit,offset=offset,items=items[offset:offset+limit])
        total = connection.execute("SELECT COUNT(*) FROM experiments").fetchone()[0]
        rows = connection.execute(
            "SELECT experiments.id, experiments.status, scenarios.code AS scenario_code, scenarios.rubric_type FROM experiments JOIN scenarios ON scenarios.id=experiments.scenario_id ORDER BY experiments.id LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return {"total": total, "limit": limit, "offset": offset, "items": [dict(r) for r in rows]}
    finally:
        connection.close()


# =========================================================
# ESCENARIOS DESDE JSON
# =========================================================
# ESCENARIOS DESDE JSON
# =========================================================

@app.get("/api/prompts/{scenario_code}")
def get_prompt(scenario_code: str):
    normalized_code = scenario_code.strip()
    prompt_data = load_prompt(normalized_code)

    if prompt_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt no encontrado",
        )

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT id FROM scenarios WHERE code = ? AND active = 1",
        (normalized_code,),
    )
    scenario = cursor.fetchone()
    connection.close()

    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Escenario no encontrado o inactivo",
        )

    _require_prompt_consistency(
        scenario_code=normalized_code,
        scenario_id=int(scenario["id"]),
    )

    return prompt_data


# =========================================================
# AGREGAR TURNO A EXPERIMENTO LIBRE
# =========================================================

@app.post(
    "/api/experiments/{experiment_id}/free-turns",
    status_code=status.HTTP_201_CREATED,
)
def add_free_turn(experiment_id: int, request: FreeTurnRequest):
    user_message = request.user_message.strip()
    if not user_message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El mensaje del usuario no puede estar vacío.",
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                experiments.id,
                experiments.status,
                experiments.scenario_id,
                experiments.scenario_snapshot_json
            FROM experiments
            WHERE experiments.id = ?
            """,
            (experiment_id,),
        )
        experiment = cursor.fetchone()

        if experiment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Experimento no encontrado.",
            )

        try:
            snapshot = json.loads(experiment["scenario_snapshot_json"] or "{}")
        except json.JSONDecodeError as error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="El snapshot del experimento está corrupto.",
            ) from error

        if snapshot.get("scenario") != "LIBRE":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Este endpoint solo está disponible para experimentos LIBRE.",
            )

        # Compatibilidad con experimentos LIBRE creados con la versión
        # anterior: si todavía apuntan a un escenario canónico, se les asigna
        # ahora un escenario exclusivo antes de insertar el primer turno.
        cursor.execute(
            "SELECT code, category, title, description, rubric_type FROM scenarios WHERE id = ?",
            (experiment["scenario_id"],),
        )
        current_scenario = cursor.fetchone()
        if current_scenario is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El escenario técnico del experimento no existe.",
            )

        if not str(current_scenario["code"]).upper().startswith("LIBRE-"):
            free_scenario_code = f"LIBRE-{experiment_id}"
            cursor.execute(
                """
                INSERT INTO scenarios (
                    code, category, title, description, rubric_type, active
                )
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (
                    free_scenario_code,
                    snapshot.get("category", current_scenario["category"]),
                    "Experimento libre",
                    "Conversación personalizada para validación del framework de EvalIA.",
                    snapshot.get("rubric_type", current_scenario["rubric_type"]),
                ),
            )
            new_scenario_id = cursor.lastrowid
            cursor.execute(
                "UPDATE experiments SET scenario_id = ? WHERE id = ?",
                (new_scenario_id, experiment_id),
            )
            experiment = dict(experiment)
            experiment["scenario_id"] = new_scenario_id

        turns = snapshot.get("turns")
        if not isinstance(turns, list):
            turns = []

        if len(turns) >= 10:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Un experimento LIBRE puede contener máximo 10 turnos.",
            )

        next_number = len(turns) + 1
        turns.append({"id": next_number, "user": user_message})
        snapshot["turns"] = turns

        serialized = json.dumps(
            snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        snapshot_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

        # Cada experimento LIBRE tiene su propio escenario técnico, por lo que
        # los turnos personalizados pueden almacenarse sin colisionar con los
        # turnos de los escenarios canónicos.
        cursor.execute(
            """
            INSERT INTO conversation_turns (scenario_id, turn_number, user_message)
            VALUES (?, ?, ?)
            """,
            (experiment["scenario_id"], next_number, user_message),
        )

        cursor.execute(
            """
            UPDATE experiments
            SET scenario_snapshot_json = ?,
                scenario_hash = ?,
                status = 'in_progress',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (serialized, snapshot_hash, experiment_id),
        )

        connection.commit()

    except HTTPException:
        connection.rollback()
        raise
    except sqlite3.IntegrityError as error:
        connection.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No fue posible agregar el turno porque ya existe en este experimento.",
        ) from error
    except Exception as error:
        connection.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible agregar el turno al experimento.",
        ) from error
    finally:
        connection.close()

    return {
        "status": "saved",
        "experiment_id": experiment_id,
        "turn": {"id": next_number, "user": user_message},
    }


# =========================================================
# RECIBIR RESPUESTAS MANUALES
# =========================================================

@app.post(
    "/api/responses/manual",
    status_code=status.HTTP_201_CREATED,
)
def save_manual_response(request: ManualResponseRequest):
    if request.experiment_id == 72:
        raise HTTPException(status_code=403, detail='El Experimento 072 está protegido; crea otro experimento.')
    response_text = request.response_text.strip()
    model_name = request.model_name.strip()

    if not response_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La respuesta no puede estar vacía",
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:
        connection.execute('BEGIN IMMEDIATE')
        cursor.execute(
            """
            SELECT
                experiments.scenario_id,
                scenarios.code AS scenario_code
            FROM experiments
            JOIN scenarios
                ON experiments.scenario_id = scenarios.id
            WHERE experiments.id = ?
            """,
            (request.experiment_id,),
        )

        experiment = cursor.fetchone()

        if experiment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Experimento no encontrado",
            )

        scenario_id = int(experiment["scenario_id"])

        try:
            snapshot = _require_experiment_snapshot_current(
                request.experiment_id,
                experiment["scenario_code"],
                scenario_id,
            )
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error

        expected_turns = {
            int(turn["id"])
            for turn in snapshot.get("turns", [])
        }

        if request.turn_number not in expected_turns:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El turno no pertenece al snapshot de este experimento",
            )

        cursor.execute(
            """
            SELECT ai_models.id
            FROM experiment_models
            JOIN ai_models
                ON experiment_models.ai_model_id = ai_models.id
            WHERE experiment_models.experiment_id = ?
              AND ai_models.name = ?
            """,
            (
                request.experiment_id,
                model_name,
            ),
        )

        model = cursor.fetchone()

        if model is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El modelo no pertenece a este experimento",
            )

        cursor.execute(
            """
            SELECT id
            FROM conversation_turns
            WHERE scenario_id = ?
              AND turn_number = ?
            """,
            (
                scenario_id,
                request.turn_number,
            ),
        )

        turn = cursor.fetchone()

        if turn is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Turno no encontrado",
            )

        cursor.execute(
            """
            SELECT id
            FROM responses
            WHERE experiment_id = ?
              AND turn_id = ?
              AND ai_model_id = ?
            """,
            (
                request.experiment_id,
                turn["id"],
                model["id"],
            ),
        )

        existing_response = cursor.fetchone()

        if existing_response is not None:
            response_id = existing_response["id"]
            original = cursor.execute("SELECT response_text FROM responses WHERE id=?", (response_id,)).fetchone()
            if original["response_text"] != response_text:
                raise HTTPException(status_code=409, detail="Este modelo y turno ya tienen una respuesta guardada; no se sobrescribe al reintentar.")
            return {"status":"saved", "action":"already_saved", "response_id":response_id,
                    "experiment_id":request.experiment_id, "model_name":model_name,
                    "turn_number":request.turn_number}

        else:
            required_previous = {n for n in expected_turns if n < request.turn_number}
            previous_rows = cursor.execute(
                "SELECT conversation_turns.turn_number FROM responses JOIN conversation_turns ON conversation_turns.id=responses.turn_id WHERE responses.experiment_id=? AND responses.ai_model_id=?",
                (request.experiment_id, model['id']),
            ).fetchall()
            if not required_previous.issubset({int(r['turn_number']) for r in previous_rows}):
                raise HTTPException(status_code=409, detail='Guarda primero los turnos anteriores de este mismo modelo. No se admite saltar el historial.')
            cursor.execute(
                """
                INSERT INTO responses (
                    experiment_id,
                    scenario_id,
                    turn_id,
                    ai_model_id,
                    response_text
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    request.experiment_id,
                    scenario_id,
                    turn["id"],
                    model["id"],
                    response_text,
                ),
            )

            response_id = cursor.lastrowid
            action = "created"

        cursor.execute(
            """
            UPDATE experiments
            SET status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                "in_progress",
                request.experiment_id,
            ),
        )

        connection.commit()

    except HTTPException:
        connection.rollback()
        raise

    except Exception as error:
        connection.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible guardar la respuesta",
        ) from error

    finally:
        connection.close()

    return {
        "status": "saved",
        "action": action,
        "response_id": response_id,
        "experiment_id": request.experiment_id,
        "model_name": model_name,
        "turn_number": request.turn_number,
    }


# =========================================================
# EVALUACIÓN DETERMINÍSTICA AUTOMÁTICA
# =========================================================
# EVALUACIÓN DETERMINÍSTICA AUTOMÁTICA
# =========================================================

@app.post(
    "/api/responses/{response_id}/evaluate",
    status_code=status.HTTP_201_CREATED,
)
def evaluate_response(response_id: int):
    from backend.integrated_evaluation import evaluate_response as integrated_evaluate
    import sys
    return integrated_evaluate(sys.modules[__name__], response_id)


# =========================================================
# CONSULTAR UNA EVALUACIÓN
# =========================================================

@app.get(
    "/api/responses/{response_id}/evaluation"
)
def get_response_evaluation(response_id: int):
    response_context = _get_response_context(response_id)

    try:
        return _load_saved_evaluation(response_id)
    except HTTPException as error:
        if error.status_code != 404:
            raise
        from backend.integrated_evaluation import load_review
        review = load_review(__import__(__name__, fromlist=["app"]), response_id)
        if review is not None:
            return review
        raise


# =========================================================
# RESULTADOS COMPARATIVOS DE UN EXPERIMENTO
# =========================================================

@app.get("/api/experiments/{experiment_id}/results")
def get_experiment_results(experiment_id: int):
    archive=getattr(app.state,'published_results',None)
    if archive and experiment_id in archive.experiment_ids:
        return archive.experiment(experiment_id)['results']
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            experiments.id,
            experiments.status,
            scenarios.id AS scenario_id,
            scenarios.code AS scenario_code,
            scenarios.title AS scenario_title,
            scenarios.category AS scenario_category,
            scenarios.rubric_type
        FROM experiments
        JOIN scenarios
            ON experiments.scenario_id = scenarios.id
        WHERE experiments.id = ?
        """,
        (experiment_id,),
    )

    experiment = cursor.fetchone()

    if experiment is None:
        _close_and_raise(
            connection,
            status.HTTP_404_NOT_FOUND,
            "Experimento no encontrado",
        )

    snapshot = _read_experiment_snapshot(experiment_id)

    snapshot_turns = {
        int(turn["id"]): turn["user"]
        for turn in snapshot.get("turns", [])
    }

    cursor.execute(
        """
        SELECT
            responses.id AS response_id,
            conversation_turns.turn_number,
            conversation_turns.user_message,
            responses.response_text,
            ai_models.id AS model_id,
            ai_models.name AS model_name,
            ai_models.provider,
            evaluations.id AS evaluation_id,
            evaluations.global_percentage,
            evaluations.classification,
            evaluations.coverage_percentage,
            evaluations.coverage_label,
            evaluations.executive_summary,
            evaluations.result_json,
            evaluations.updated_at AS evaluated_at
        FROM responses
        JOIN conversation_turns
            ON responses.turn_id = conversation_turns.id
        JOIN ai_models
            ON responses.ai_model_id = ai_models.id
        LEFT JOIN evaluations
            ON evaluations.response_id = responses.id
        WHERE responses.experiment_id = ?
        ORDER BY conversation_turns.turn_number, ai_models.name
        """,
        (experiment_id,),
    )

    rows = cursor.fetchall()

    cursor.execute(
        """
        SELECT
            conversation_evaluations.id,
            conversation_evaluations.ai_model_id,
            conversation_evaluations.global_percentage,
            conversation_evaluations.classification,
            conversation_evaluations.coverage_percentage,
            conversation_evaluations.coverage_label,
            conversation_evaluations.executive_summary,
            conversation_evaluations.public_result_json,
            conversation_evaluations.updated_at,
            ai_models.name AS model_name,
            ai_models.provider
        FROM conversation_evaluations
        JOIN ai_models
            ON conversation_evaluations.ai_model_id = ai_models.id
        WHERE conversation_evaluations.experiment_id = ?
        ORDER BY ai_models.name
        """,
        (experiment_id,),
    )

    conversation_rows = cursor.fetchall()
    connection.close()

    is_free = snapshot.get("scenario") == "LIBRE"

    scenario_code = "LIBRE" if is_free else experiment["scenario_code"]
    scenario_title = (
        snapshot.get("title", "Experimento libre")
        if is_free
        else experiment["scenario_title"]
    )
    rubric_type = (
        snapshot.get("rubric_type", experiment["rubric_type"])
        if is_free
        else experiment["rubric_type"]
    )

    results = []

    for row in rows:
        public_json = None

        if row["result_json"]:
            try:
                public_json = json.loads(row["result_json"])
            except json.JSONDecodeError:
                pass

        turn_number = int(row["turn_number"])
        user_message = (
            snapshot_turns.get(turn_number, row["user_message"])
            if is_free
            else row["user_message"]
        )

        results.append({
            "response_id": row["response_id"],
            "turn_number": turn_number,
            "user_message": user_message,
            "response_text": row["response_text"],
            "model": {
                "id": row["model_id"],
                "name": row["model_name"],
                "provider": row["provider"],
            },
            "evaluated": row["evaluation_id"] is not None,
            "evaluation": ({
                "evaluation_id": row["evaluation_id"],
                "global_percentage": row["global_percentage"],
                "classification": row["classification"],
                "coverage": {
                    "percentage": row["coverage_percentage"],
                    "label": row["coverage_label"],
                },
                "executive_summary": row["executive_summary"],
                "evaluated_at": row["evaluated_at"],
                "result": public_json,
                "indicators": _load_evaluation_indicators(
                    int(row["evaluation_id"])
                ),
            } if row["evaluation_id"] is not None else None),
        })

    conversation_results = []

    for row in conversation_rows:
        try:
            public_json = json.loads(
                row["public_result_json"]
            )
        except (TypeError, json.JSONDecodeError):
            public_json = None

        conversation_results.append({
            "conversation_evaluation_id": row["id"],
            "model": {
                "id": row["ai_model_id"],
                "name": row["model_name"],
                "provider": row["provider"],
            },
            "global_percentage": row["global_percentage"],
            "classification": row["classification"],
            "coverage": {
                "percentage": row["coverage_percentage"],
                "label": row["coverage_label"],
            },
            "executive_summary": row["executive_summary"],
            "evaluated_at": row["updated_at"],
            "result": public_json,
        })

    from backend.integrated_evaluation import load_review
    import sys
    for item in results:
        if item["evaluated"]:
            continue
        review = load_review(sys.modules[__name__], item["response_id"])
        if review is None:
            continue
        public = review["result"]
        native = public.get("validated_audit", {}).get("indicator_results", [])
        item["evaluated"] = True
        item["review_required"] = review["review_required"]
        item["evaluation"] = dict(evaluation_id=None, review_id=review["review_id"],
            global_percentage=None, classification=public["global_result"]["classification"],
            coverage=public["global_result"]["coverage"], executive_summary=public["executive_summary"],
            result=public, indicators=public.get("indicator_details", []))
    evaluated_count = sum(
        1 for item in results if item["evaluated"] and not item.get("review_required")
    )

    payload = {
        "experiment": {
            "id": experiment["id"],
            "status": experiment["status"],
            "scenario_code": scenario_code,
            "scenario_title": scenario_title,
            "rubric_type": rubric_type,
        },
        "summary": {
            "responses_saved": len(results),
            "responses_evaluated": evaluated_count,
            "responses_pending_evaluation": (
                len(results) - evaluated_count
            ),
            "conversation_evaluations": len(conversation_results),
        },
        "results": results,
        "conversation_results": conversation_results,
        "models": get_experiment(experiment_id)["models"],
    }
    config = getattr(app.state, 'direct_recovery_config', None)
    if config:
        from governed.direct_presentation import apply
        return apply(payload, config, app.state.direct_recovery_database)
    return payload


# =========================================================
# EXPORTACIÓN DE EXPERIMENTOS
# =========================================================
# EXPORTACIÓN DE EXPERIMENTOS
# =========================================================
@app.get("/api/experiments/{experiment_id}/export.pdf")
def export_experiment_pdf(experiment_id: int):
    """Descarga los resultados guardados en PDF."""

    payload = get_experiment_results(experiment_id)
    if payload.get('hybrid_recovery'):
        from copy import deepcopy
        payload = deepcopy(payload)
        for turn in payload['results']:
            indicators = turn['evaluation']['indicators']
            missing = [r for r in indicators if r.get('status') not in ('SCORED', 'N/A')]
            turn['evaluation']['indicators'] = [r for r in indicators if r.get('status') in ('SCORED', 'N/A')]
            note = ' No calificado (excluido del cálculo): ' + '; '.join(r['indicator_code'] + ': ' + r['justification'] for r in missing) if missing else ''
            turn['evaluation']['executive_summary'] += note
            turn['evaluation']['result']['executive_summary'] += note
    document = BytesIO(build_results_pdf(payload))

    return StreamingResponse(
        document,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="EvalIA_experimento_'
                f'{experiment_id:04d}_resultados.pdf"'
            )
        },
    )

@app.get("/api/experiments/{experiment_id}/export.xlsx")
def export_experiment_excel(experiment_id: int):
    # Same persisted canonical read as the results endpoint, including reviews.
    canonical_payload = get_experiment_results(experiment_id)
    if canonical_payload.get('hybrid_recovery'):
        from governed.direct_presentation import excel
        return excel(canonical_payload)
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT experiments.id,
               experiments.status,
               experiments.created_at,
               experiments.updated_at,
               scenarios.code AS scenario_code,
               scenarios.title AS scenario_title,
               scenarios.rubric_type
        FROM experiments
        JOIN scenarios ON experiments.scenario_id = scenarios.id
        WHERE experiments.id = ?
        """,
        (experiment_id,),
    )
    experiment = cursor.fetchone()

    if experiment is None:
        _close_and_raise(
            connection,
            status.HTTP_404_NOT_FOUND,
            "Experimento no encontrado",
        )

    cursor.execute(
        "SELECT scenario_id FROM experiments WHERE id = ?",
        (experiment_id,),
    )
    scenario_row = cursor.fetchone()

    if scenario_row is None:
        _close_and_raise(
            connection,
            status.HTTP_404_NOT_FOUND,
            "Experimento no encontrado",
        )

    snapshot = _read_experiment_snapshot(experiment_id)

    cursor.execute(
        """
        SELECT conversation_turns.turn_number,
               conversation_turns.user_message,
               responses.response_text,
               ai_models.name AS model_name,
               ai_models.provider,
               evaluations.global_percentage,
               evaluations.classification,
               evaluations.coverage_percentage,
               evaluations.coverage_label,
               evaluations.executive_summary,
               evaluations.result_json,
               evaluations.updated_at AS evaluated_at
        FROM responses
        JOIN conversation_turns
             ON responses.turn_id = conversation_turns.id
        JOIN ai_models
             ON responses.ai_model_id = ai_models.id
        LEFT JOIN evaluations
             ON evaluations.response_id = responses.id
        WHERE responses.experiment_id = ?
        ORDER BY conversation_turns.turn_number, ai_models.name
        """,
        (experiment_id,),
    )
    response_rows = cursor.fetchall()

    response_rows = [dict(row) for row in response_rows]
    canonical_by_pair = {(item['turn_number'], item['model']['name']): item
                         for item in canonical_payload.get('results', [])}
    for row in response_rows:
        item = canonical_by_pair.get((row['turn_number'], row['model_name'])) or {}
        if (item.get('evaluation') or {}).get('review_id') is not None:
            evaluation = item.get('evaluation') or {}
            public = evaluation.get('result') or {}
            row.update(global_percentage=None, classification=evaluation.get('classification'),
                       executive_summary=evaluation.get('executive_summary'),
                       coverage_percentage=(evaluation.get('coverage') or {}).get('percentage'),
                       coverage_label=(evaluation.get('coverage') or {}).get('label'),
                       result_json=json.dumps(public, ensure_ascii=False))

    cursor.execute(
        """
        SELECT ai_models.name AS model_name,
               ai_models.provider,
               conversation_evaluations.global_percentage,
               conversation_evaluations.classification,
               conversation_evaluations.coverage_percentage,
               conversation_evaluations.coverage_label,
               conversation_evaluations.executive_summary,
               conversation_evaluations.public_result_json,
               conversation_evaluations.updated_at
        FROM conversation_evaluations
        JOIN ai_models
             ON conversation_evaluations.ai_model_id = ai_models.id
        WHERE conversation_evaluations.experiment_id = ?
        ORDER BY ai_models.name
        """,
        (experiment_id,),
    )
    conversation_rows = cursor.fetchall()

    connection.close()

    workbook = Workbook()

    # -----------------------------------------------------
    # HOJA 1: INFORMACIÓN GENERAL
    # -----------------------------------------------------

    ws_info = workbook.active
    ws_info.title = "Experimento"

    is_free = snapshot.get("scenario") == "LIBRE"

    export_scenario_code = (
        "LIBRE" if is_free else experiment["scenario_code"]
    )
    export_scenario_title = (
        snapshot.get("title", "Experimento libre")
        if is_free
        else experiment["scenario_title"]
    )
    export_rubric_type = (
        snapshot.get("rubric_type", experiment["rubric_type"])
        if is_free
        else experiment["rubric_type"]
    )

    snapshot_turns = {
        int(turn["id"]): turn["user"]
        for turn in snapshot.get("turns", [])
    }

    info_rows = [
        ("Campo", "Valor"),
        ("ID experimento", experiment["id"]),
        ("Estado", experiment["status"]),
        ("Código escenario", export_scenario_code),
        ("Escenario", export_scenario_title),
        ("Rúbrica", export_rubric_type),
        ("Creado", experiment["created_at"]),
        ("Actualizado", experiment["updated_at"]),
        ("Respuestas almacenadas", len(response_rows)),
        ("Evaluaciones longitudinales", len(conversation_rows)),
    ]

    for row in info_rows:
        ws_info.append(row)

    # -----------------------------------------------------
    # HOJA 2: CONVERSACIONES
    # -----------------------------------------------------

    ws_conv = workbook.create_sheet("Conversaciones")

    ws_conv.append([
        "Turno",
        "Modelo",
        "Proveedor",
        "Mensaje del usuario",
        "Respuesta de la IA",
        "Resultado turno (%)",
        "Clasificación",
        "Cobertura (%)",
        "Cobertura nivel",
        "Resumen ejecutivo",
        "Fecha evaluación",
    ])

    for row in response_rows:
        turn_number = int(row["turn_number"])
        user_message = (
            snapshot_turns.get(turn_number, row["user_message"])
            if is_free
            else row["user_message"]
        )

        ws_conv.append([
            turn_number,
            row["model_name"],
            row["provider"],
            user_message,
            row["response_text"],
            row["global_percentage"],
            row["classification"],
            row["coverage_percentage"],
            row["coverage_label"],
            row["executive_summary"],
            row["evaluated_at"],
        ])

    # -----------------------------------------------------
    # HOJA 3: RESULTADOS LONGITUDINALES
    # -----------------------------------------------------

    ws_long = workbook.create_sheet("Resultados longitudinales")

    ws_long.append([
        "Modelo",
        "Proveedor",
        "Resultado global (%)",
        "Clasificación",
        "Cobertura (%)",
        "Cobertura nivel",
        "Resumen ejecutivo",
        "Fecha evaluación",
    ])

    for row in conversation_rows:
        ws_long.append([
            row["model_name"],
            row["provider"],
            row["global_percentage"],
            row["classification"],
            row["coverage_percentage"],
            row["coverage_label"],
            row["executive_summary"],
            row["updated_at"],
        ])

    # -----------------------------------------------------
    # HOJA 4: CRITERIOS LONGITUDINALES
    # -----------------------------------------------------

    ws_criteria = workbook.create_sheet("Criterios")

    ws_criteria.append([
        "Modelo",
        "Código criterio",
        "Criterio",
        "Puntaje 0-3",
        "Nivel rúbrica",
        "Porcentaje",
        "Clasificación",
        "Estado",
        "Cobertura (%)",
        "Indicadores aplicables",
        "Indicadores N/A",
        "Total indicadores",
        "Fallo crítico",
    ])

    for row in conversation_rows:
        if not row["public_result_json"]:
            continue

        try:
            public_result = json.loads(row["public_result_json"])
        except json.JSONDecodeError:
            continue

        for criterion in public_result.get("criteria", []):
            coverage = criterion.get("coverage") or {}

            ws_criteria.append([
                row["model_name"],
                criterion.get("criterion_code"),
                criterion.get("criterion_name"),
                criterion.get("score_0_to_3"),
                criterion.get("rubric_level"),
                criterion.get("percentage"),
                criterion.get("classification"),
                criterion.get("status"),
                coverage.get("percentage"),
                criterion.get("applicable_indicators"),
                criterion.get("not_applicable_indicators"),
                criterion.get("total_indicators"),
                criterion.get("has_critical_failure"),
            ])

    # -----------------------------------------------------
    # FORMATO
    # -----------------------------------------------------

    from backend.export_audit import append_xlsx_audit
    append_xlsx_audit(workbook, canonical_payload)

    header_fill = PatternFill(
        fill_type="solid",
        fgColor="EDE9FE",
    )

    for worksheet in workbook.worksheets:
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions

        for cell in worksheet[1]:
            cell.font = Font(bold=True)
            cell.fill = header_fill
            cell.alignment = Alignment(
                vertical="center",
                wrap_text=True,
            )

        for row in worksheet.iter_rows():
            for cell in row:
                cell.alignment = Alignment(
                    vertical="top",
                    wrap_text=True,
                )

        for column_cells in worksheet.columns:
            column_letter = column_cells[0].column_letter

            max_length = 0
            for cell in column_cells:
                value = "" if cell.value is None else str(cell.value)
                max_length = max(max_length, len(value))

            worksheet.column_dimensions[column_letter].width = min(
                max(max_length + 2, 12),
                55,
            )

    ws_conv.column_dimensions["D"].width = 55
    ws_conv.column_dimensions["E"].width = 75
    ws_conv.column_dimensions["J"].width = 65
    ws_long.column_dimensions["G"].width = 75

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    filename = f"EvalIA_experimento_{experiment_id:04d}.xlsx"

    return StreamingResponse(
        output,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            )
        },
    )


@app.get("/api/experiments/{experiment_id}/export.json")
def export_experiment_json(experiment_id: int):
    """Download the canonical persisted result, including null and review states."""
    import json
    from fastapi.encoders import jsonable_encoder
    from fastapi.responses import Response

    payload = get_experiment_results(experiment_id)
    content = json.dumps(jsonable_encoder(payload), ensure_ascii=False,
                         allow_nan=False, indent=2).encode("utf-8")
    return Response(content, media_type="application/json",
                    headers={"Content-Disposition":
                             f'attachment; filename="EvalIA_experimento_{experiment_id:04d}.json"'})


# Local REAL mode is prepared, never activated by importing the application.
from backend.luna_real_ui import mount as _mount_luna_real_ui
import sys as _sys
_mount_luna_real_ui(_sys.modules[__name__])
from backend.global_results import mount as _mount_global_results
_mount_global_results(_sys.modules[__name__])
