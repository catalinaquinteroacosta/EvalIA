from __future__ import annotations

import json
from pathlib import Path

from database import get_connection, create_tables


BASE_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = BASE_DIR / "database" / "prompts"

VALID_CATEGORIES = {
    "Ansiedad": "trastorno",
    "Depresión": "trastorno",
    "Crisis de pareja": "crisis",
    "Crisis existencial": "crisis",
    "Crisis social": "crisis",
}


def load_prompt_file(file_path: Path) -> dict:
    """
    Carga y valida un escenario canónico desde database/prompts.
    """

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

    except json.JSONDecodeError as error:
        raise ValueError(
            f"JSON inválido en '{file_path.name}': {error}"
        ) from error

    if not isinstance(data, dict):
        raise ValueError(
            f"El archivo '{file_path.name}' debe contener un objeto JSON."
        )

    scenario_code = data.get("scenario")
    title = data.get("title")
    category = data.get("category")
    turns = data.get("turns")

    if not isinstance(scenario_code, str) or not scenario_code.strip():
        raise ValueError(
            f"El archivo '{file_path.name}' no tiene un 'scenario' válido."
        )

    scenario_code = scenario_code.strip()

    if scenario_code != file_path.stem:
        raise ValueError(
            f"El archivo '{file_path.name}' declara scenario='{scenario_code}', "
            f"pero el nombre del archivo corresponde a '{file_path.stem}'."
        )

    if not isinstance(title, str) or not title.strip():
        raise ValueError(
            f"El escenario '{scenario_code}' no tiene un 'title' válido."
        )

    title = title.strip()

    if not isinstance(category, str) or not category.strip():
        raise ValueError(
            f"El escenario '{scenario_code}' no tiene una 'category' válida."
        )

    category = category.strip()

    if category not in VALID_CATEGORIES:
        raise ValueError(
            f"Categoría no reconocida en '{scenario_code}': '{category}'."
        )

    rubric_type = VALID_CATEGORIES[category]

    if not isinstance(turns, list) or not turns:
        raise ValueError(
            f"El escenario '{scenario_code}' no contiene una lista válida de turnos."
        )

    normalized_turns = []
    seen_turn_numbers = set()

    for position, turn in enumerate(turns, start=1):

        if not isinstance(turn, dict):
            raise ValueError(
                f"Turno inválido en '{scenario_code}', posición {position}."
            )

        turn_number = turn.get("id")
        user_message = turn.get("user")

        if not isinstance(turn_number, int) or turn_number <= 0:
            raise ValueError(
                f"El escenario '{scenario_code}' tiene un id de turno inválido "
                f"en la posición {position}."
            )

        if turn_number in seen_turn_numbers:
            raise ValueError(
                f"El escenario '{scenario_code}' tiene repetido "
                f"el turno {turn_number}."
            )

        if not isinstance(user_message, str) or not user_message.strip():
            raise ValueError(
                f"El escenario '{scenario_code}' tiene un mensaje vacío "
                f"en el turno {turn_number}."
            )

        seen_turn_numbers.add(turn_number)

        normalized_turns.append(
            {
                "turn_number": turn_number,
                "user_message": user_message.strip(),
            }
        )

    normalized_turns.sort(
        key=lambda item: item["turn_number"]
    )

    actual_numbers = [
        item["turn_number"]
        for item in normalized_turns
    ]

    expected_numbers = list(
        range(1, len(normalized_turns) + 1)
    )

    if actual_numbers != expected_numbers:
        raise ValueError(
            f"Los turnos de '{scenario_code}' deben ser consecutivos "
            f"desde 1. Encontrados: {actual_numbers}."
        )

    if len(normalized_turns) != 5:
        raise ValueError(
            f"El escenario '{scenario_code}' debe contener exactamente "
            f"5 turnos. Encontrados: {len(normalized_turns)}."
        )

    return {
        "scenario": scenario_code,
        "title": title,
        "category": category,
        "description": title,
        "rubric_type": rubric_type,
        "turns": normalized_turns,
    }


def sync_scenario(cursor, prompt_data: dict) -> dict:
    """
    Crea el escenario en SQLite si no existe.

    Si ya existe, sincroniza sus metadatos con el JSON canónico.
    """

    scenario_code = prompt_data["scenario"]

    cursor.execute(
        """
        SELECT
            id,
            category,
            title,
            description,
            rubric_type,
            active
        FROM scenarios
        WHERE code = ?
        """,
        (scenario_code,),
    )

    existing = cursor.fetchone()

    if existing is None:

        cursor.execute(
            """
            INSERT INTO scenarios (
                code,
                category,
                title,
                description,
                rubric_type,
                active
            )
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (
                scenario_code,
                prompt_data["category"],
                prompt_data["title"],
                prompt_data["description"],
                prompt_data["rubric_type"],
            ),
        )

        return {
            "scenario_id": int(cursor.lastrowid),
            "action": "created",
        }

    scenario_id = int(existing["id"])

    metadata_changed = (
        existing["category"] != prompt_data["category"]
        or existing["title"] != prompt_data["title"]
        or existing["description"] != prompt_data["description"]
        or existing["rubric_type"] != prompt_data["rubric_type"]
        or int(existing["active"]) != 1
    )

    if metadata_changed:

        cursor.execute(
            """
            UPDATE scenarios
            SET category = ?,
                title = ?,
                description = ?,
                rubric_type = ?,
                active = 1
            WHERE id = ?
            """,
            (
                prompt_data["category"],
                prompt_data["title"],
                prompt_data["description"],
                prompt_data["rubric_type"],
                scenario_id,
            ),
        )

        action = "updated"

    else:
        action = "unchanged"

    return {
        "scenario_id": scenario_id,
        "action": action,
    }


def sync_scenario_turns(
    cursor,
    scenario_id: int,
    prompt_data: dict,
) -> dict:
    """
    Sincroniza los cinco turnos del escenario con conversation_turns.

    Conserva los IDs existentes cuando el turno ya está registrado.
    """

    scenario_code = prompt_data["scenario"]

    created = 0
    updated = 0
    unchanged = 0

    expected_turn_numbers = {
        turn["turn_number"]
        for turn in prompt_data["turns"]
    }

    cursor.execute(
        """
        SELECT id, turn_number
        FROM conversation_turns
        WHERE scenario_id = ?
        """,
        (scenario_id,),
    )

    existing_rows = cursor.fetchall()

    unexpected_turns = [
        int(row["turn_number"])
        for row in existing_rows
        if int(row["turn_number"]) not in expected_turn_numbers
    ]

    if unexpected_turns:
        raise ValueError(
            f"SQLite contiene turnos no definidos por el JSON canónico "
            f"de '{scenario_code}': {unexpected_turns}. "
            "No se eliminarán automáticamente."
        )

    for turn in prompt_data["turns"]:

        turn_number = turn["turn_number"]
        user_message = turn["user_message"]

        cursor.execute(
            """
            SELECT id, user_message
            FROM conversation_turns
            WHERE scenario_id = ?
              AND turn_number = ?
            """,
            (
                scenario_id,
                turn_number,
            ),
        )

        existing = cursor.fetchone()

        if existing is None:

            cursor.execute(
                """
                INSERT INTO conversation_turns (
                    scenario_id,
                    turn_number,
                    user_message
                )
                VALUES (?, ?, ?)
                """,
                (
                    scenario_id,
                    turn_number,
                    user_message,
                ),
            )

            created += 1

        elif existing["user_message"] != user_message:

            cursor.execute(
                """
                UPDATE conversation_turns
                SET user_message = ?
                WHERE id = ?
                """,
                (
                    user_message,
                    existing["id"],
                ),
            )

            updated += 1

        else:
            unchanged += 1

    return {
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
    }


def sync_all_prompt_files(cursor) -> list[dict]:
    """
    Descubre automáticamente todos los JSON del banco de escenarios.

    Cada JSON es la fuente canónica para:
    - código
    - título
    - categoría
    - tipo de rúbrica
    - cinco turnos
    """

    if not PROMPTS_DIR.exists():
        raise ValueError(
            f"No existe el directorio de prompts: {PROMPTS_DIR}"
        )

    prompt_files = sorted(
        PROMPTS_DIR.glob("*.json")
    )

    if not prompt_files:
        raise ValueError(
            f"No se encontraron archivos JSON en: {PROMPTS_DIR}"
        )

    results = []

    seen_scenarios = set()

    for file_path in prompt_files:

        prompt_data = load_prompt_file(file_path)

        scenario_code = prompt_data["scenario"]

        if scenario_code in seen_scenarios:
            raise ValueError(
                f"Escenario duplicado en el banco: '{scenario_code}'."
            )

        seen_scenarios.add(scenario_code)

        scenario_result = sync_scenario(
            cursor,
            prompt_data,
        )

        turn_result = sync_scenario_turns(
            cursor,
            scenario_result["scenario_id"],
            prompt_data,
        )

        results.append(
            {
                "scenario": scenario_code,
                "scenario_action": scenario_result["action"],
                "turns_created": turn_result["created"],
                "turns_updated": turn_result["updated"],
                "turns_unchanged": turn_result["unchanged"],
            }
        )

    return results


def main():
    create_tables()

    connection = get_connection()
    cursor = connection.cursor()

    try:

        results = sync_all_prompt_files(cursor)

        total_scenarios = len(results)
        total_turns = sum(
            result["turns_created"]
            + result["turns_updated"]
            + result["turns_unchanged"]
            for result in results
        )

        if total_scenarios != 38:
            raise ValueError(
                f"Se esperaban 38 escenarios canónicos, "
                f"pero se encontraron {total_scenarios}."
            )

        if total_turns != 190:
            raise ValueError(
                f"Se esperaban 190 turnos canónicos, "
                f"pero se procesaron {total_turns}."
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    print()
    print("Banco canónico de EvalIA sincronizado correctamente.")
    print(f"Escenarios procesados: {total_scenarios}")
    print(f"Turnos procesados: {total_turns}")
    print()

    for result in results:
        print(
            f"{result['scenario']}: "
            f"escenario={result['scenario_action']}, "
            f"turnos_creados={result['turns_created']}, "
            f"turnos_actualizados={result['turns_updated']}, "
            f"turnos_sin_cambios={result['turns_unchanged']}"
        )


if __name__ == "__main__":
    main()