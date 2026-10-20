import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_DIR = BASE_DIR / "database"
DB_PATH = DATABASE_DIR / "evalia.db"


def get_connection() -> sqlite3.Connection:
    """
    Abre una conexión a SQLite con claves foráneas activadas.
    """
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")

    return connection


def _table_exists(
    cursor: sqlite3.Cursor,
    table_name: str,
) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    )
    return cursor.fetchone() is not None


def _get_table_columns(
    cursor: sqlite3.Cursor,
    table_name: str,
) -> set[str]:
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {
        row["name"]
        for row in cursor.fetchall()
    }

def _add_column_if_missing(
    cursor: sqlite3.Cursor,
    table_name: str,
    column_name: str,
    column_definition: str,
) -> None:
    """
    Agrega una columna a una tabla existente únicamente si todavía
    no está presente.
    """
    columns = _get_table_columns(cursor, table_name)

    if column_name not in columns:
        cursor.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_name} {column_definition}
            """
        )


def _migrate_legacy_evaluations(
    cursor: sqlite3.Cursor,
) -> None:
    """
    Migra la tabla antigua 'evaluations', que almacenaba un registro
    por criterio, para permitir la nueva estructura de EvalIA.

    La tabla anterior se conserva como 'legacy_evaluations'.
    """
    if not _table_exists(cursor, "evaluations"):
        return

    columns = _get_table_columns(
        cursor,
        "evaluations",
    )

    legacy_columns = {
        "criterion_id",
        "score",
    }

    new_columns = {
        "rubric_type",
        "global_percentage",
        "result_json",
    }

    if legacy_columns.issubset(columns) and not new_columns.issubset(columns):
        if not _table_exists(cursor, "legacy_evaluations"):
            cursor.execute(
                """
                ALTER TABLE evaluations
                RENAME TO legacy_evaluations
                """
            )
        else:
            cursor.execute(
                """
                DROP TABLE evaluations
                """
            )


def create_tables() -> None:
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                provider TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
                    CHECK (active IN (0, 1))
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS scenarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                rubric_type TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
                    CHECK (active IN (0, 1))
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scenario_id INTEGER NOT NULL,
                turn_number INTEGER NOT NULL,
                user_message TEXT NOT NULL,
                FOREIGN KEY (scenario_id)
                    REFERENCES scenarios(id)
                    ON DELETE CASCADE,
                UNIQUE (scenario_id, turn_number)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scenario_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'created',
                scenario_snapshot_json TEXT,
                scenario_hash TEXT,
                created_at TIMESTAMP NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (scenario_id)
                    REFERENCES scenarios(id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS experiment_models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id INTEGER NOT NULL,
                ai_model_id INTEGER NOT NULL,
                FOREIGN KEY (experiment_id)
                    REFERENCES experiments(id)
                    ON DELETE CASCADE,
                FOREIGN KEY (ai_model_id)
                    REFERENCES ai_models(id),
                UNIQUE (experiment_id, ai_model_id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id INTEGER NOT NULL,
                scenario_id INTEGER NOT NULL,
                turn_id INTEGER NOT NULL,
                ai_model_id INTEGER NOT NULL,
                response_text TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (experiment_id)
                    REFERENCES experiments(id)
                    ON DELETE CASCADE,
                FOREIGN KEY (scenario_id)
                    REFERENCES scenarios(id),
                FOREIGN KEY (turn_id)
                    REFERENCES conversation_turns(id),
                FOREIGN KEY (ai_model_id)
                    REFERENCES ai_models(id),
                UNIQUE (
                    experiment_id,
                    turn_id,
                    ai_model_id
                )
            )
            """
        )

                # =====================================================
        # MIGRACIONES DE TABLAS EXISTENTES
        # =====================================================

        _add_column_if_missing(
            cursor,
            "ai_models",
            "active",
            "INTEGER NOT NULL DEFAULT 1",
        )

        _add_column_if_missing(
            cursor,
            "scenarios",
            "active",
            "INTEGER NOT NULL DEFAULT 1",
        )

        _add_column_if_missing(
            cursor,
            "experiments",
            "updated_at",
            "TIMESTAMP",
        )

        # Snapshot inmutable del escenario utilizado por cada experimento.
        # Las columnas son NULL para experimentos históricos creados antes
        # de esta migración; no se rellenan automáticamente para evitar
        # atribuirles un estímulo que no pueda demostrarse.
        _add_column_if_missing(
            cursor,
            "experiments",
            "scenario_snapshot_json",
            "TEXT",
        )

        _add_column_if_missing(
            cursor,
            "experiments",
            "scenario_hash",
            "TEXT",
        )

        _add_column_if_missing(
            cursor,
            "responses",
            "updated_at",
            "TIMESTAMP",
        )

        cursor.execute(
            """
            UPDATE experiments
            SET updated_at = COALESCE(updated_at, created_at)
            """
        )

        cursor.execute(
            """
            UPDATE responses
            SET updated_at = COALESCE(updated_at, created_at)
            """
        )

        # Tabla heredada del diseño inicial. Se conserva para no romper
        # datos antiguos, pero las rúbricas activas se leen desde JSON.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS rubric_criteria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rubric_type TEXT NOT NULL,
                code TEXT,
                name TEXT NOT NULL,
                description TEXT,
                score_0 TEXT,
                score_1 TEXT,
                score_2 TEXT,
                score_3 TEXT,
                UNIQUE (rubric_type, code)
            )
            """
        )

        _migrate_legacy_evaluations(cursor)

        # Un registro por evaluación completa de una respuesta.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                response_id INTEGER NOT NULL,
                rubric_type TEXT NOT NULL,
                rubric_name TEXT NOT NULL,
                rubric_version TEXT NOT NULL,
                evaluator_type TEXT NOT NULL
                    DEFAULT 'deterministic_rules',
                evaluator_model TEXT,
                global_percentage REAL NOT NULL
                    CHECK (
                        global_percentage >= 0
                        AND global_percentage <= 100
                    ),
                classification TEXT NOT NULL,
                classification_before_critical_rules TEXT,
                applicable_indicators INTEGER NOT NULL DEFAULT 0,
                not_applicable_indicators INTEGER NOT NULL DEFAULT 0,
                total_indicators INTEGER NOT NULL DEFAULT 0,
                coverage_percentage REAL NOT NULL DEFAULT 0,
                coverage_label TEXT NOT NULL DEFAULT 'Sin cobertura',
                executive_summary TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (response_id)
                    REFERENCES responses(id)
                    ON DELETE CASCADE,
                UNIQUE (response_id)
            )
            """
        )

        # Resultado visible consolidado por criterio.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS evaluation_criteria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evaluation_id INTEGER NOT NULL,
                criterion_code TEXT NOT NULL,
                criterion_name TEXT NOT NULL,
                criterion_order INTEGER NOT NULL DEFAULT 0,
                score_0_to_3 REAL,
                percentage REAL,
                classification TEXT NOT NULL,
                total_score INTEGER NOT NULL DEFAULT 0,
                maximum_score INTEGER NOT NULL DEFAULT 0,
                applicable_indicators INTEGER NOT NULL DEFAULT 0,
                not_applicable_indicators INTEGER NOT NULL DEFAULT 0,
                total_indicators INTEGER NOT NULL DEFAULT 0,
                coverage_percentage REAL NOT NULL DEFAULT 0,
                coverage_label TEXT NOT NULL DEFAULT 'Sin cobertura',
                has_critical_failure INTEGER NOT NULL DEFAULT 0
                    CHECK (has_critical_failure IN (0, 1)),
                critical_failure_count INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (evaluation_id)
                    REFERENCES evaluations(id)
                    ON DELETE CASCADE,
                UNIQUE (evaluation_id, criterion_code)
            )
            """
        )

        # Detalle interno. No se muestra normalmente al usuario final.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS evaluation_indicators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evaluation_id INTEGER NOT NULL,
                criterion_code TEXT NOT NULL,
                indicator_code TEXT NOT NULL,
                applicable INTEGER NOT NULL
                    CHECK (applicable IN (0, 1)),
                score INTEGER
                    CHECK (
                        score IS NULL
                        OR score IN (0, 1, 2, 3)
                    ),
                justification TEXT NOT NULL,
                indicator_type TEXT NOT NULL,
                criticality TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'normal',
                critical_failure INTEGER NOT NULL DEFAULT 0
                    CHECK (critical_failure IN (0, 1)),
                FOREIGN KEY (evaluation_id)
                    REFERENCES evaluations(id)
                    ON DELETE CASCADE,
                UNIQUE (evaluation_id, indicator_code)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS evaluation_strengths (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evaluation_id INTEGER NOT NULL,
                position INTEGER NOT NULL,
                text TEXT NOT NULL,
                FOREIGN KEY (evaluation_id)
                    REFERENCES evaluations(id)
                    ON DELETE CASCADE,
                UNIQUE (evaluation_id, position)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS evaluation_improvements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evaluation_id INTEGER NOT NULL,
                position INTEGER NOT NULL,
                text TEXT NOT NULL,
                FOREIGN KEY (evaluation_id)
                    REFERENCES evaluations(id)
                    ON DELETE CASCADE,
                UNIQUE (evaluation_id, position)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS evaluation_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evaluation_id INTEGER NOT NULL,
                indicator_code TEXT NOT NULL,
                criterion_code TEXT NOT NULL,
                criterion_name TEXT NOT NULL,
                priority TEXT NOT NULL,
                score INTEGER,
                message TEXT NOT NULL,
                FOREIGN KEY (evaluation_id)
                    REFERENCES evaluations(id)
                    ON DELETE CASCADE,
                UNIQUE (evaluation_id, indicator_code)
            )
            """
        )

        # Evaluación longitudinal final de una conversación completa.
        # Existe un registro por modelo dentro de cada experimento y NO
        # sustituye las evaluaciones individuales de los turnos.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id INTEGER NOT NULL,
                ai_model_id INTEGER NOT NULL,
                rubric_type TEXT NOT NULL,
                rubric_name TEXT NOT NULL,
                rubric_version TEXT NOT NULL,
                evaluator_type TEXT NOT NULL
                    DEFAULT 'deterministic_rules',
                global_percentage REAL NOT NULL
                    CHECK (
                        global_percentage >= 0
                        AND global_percentage <= 100
                    ),
                classification TEXT NOT NULL,
                classification_before_critical_rules TEXT,
                applicable_indicators INTEGER NOT NULL DEFAULT 0,
                not_applicable_indicators INTEGER NOT NULL DEFAULT 0,
                total_indicators INTEGER NOT NULL DEFAULT 0,
                coverage_percentage REAL NOT NULL DEFAULT 0,
                coverage_label TEXT NOT NULL DEFAULT 'Sin cobertura',
                executive_summary TEXT NOT NULL,
                internal_result_json TEXT NOT NULL,
                public_result_json TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (experiment_id)
                    REFERENCES experiments(id)
                    ON DELETE CASCADE,
                FOREIGN KEY (ai_model_id)
                    REFERENCES ai_models(id),
                UNIQUE (experiment_id, ai_model_id)
            )
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_experiments_scenario
            ON experiments (scenario_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_responses_experiment
            ON responses (experiment_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_responses_model
            ON responses (ai_model_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_conversation_evaluations_experiment
            ON conversation_evaluations (experiment_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_conversation_evaluations_model
            ON conversation_evaluations (ai_model_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_evaluations_response
            ON evaluations (response_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_evaluation_criteria_evaluation
            ON evaluation_criteria (evaluation_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_evaluation_indicators_evaluation
            ON evaluation_indicators (evaluation_id)
            """
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    create_tables()
    print(
        "Base de datos de EvalIA creada o actualizada correctamente."
    )

