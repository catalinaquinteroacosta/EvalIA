from database import create_tables, get_connection
from rubric_loader import load_rubric


def import_rubric(rubric_name: str) -> int:
    rubric = load_rubric(rubric_name)

    if rubric is None:
        raise ValueError(
            f"No se encontró la rúbrica '{rubric_name}'."
        )

    connection = get_connection()
    cursor = connection.cursor()

    imported_count = 0

    for criterion in rubric["criteria"]:
        criterion_code = criterion["code"]
        criterion_name = criterion["name"]
        levels = criterion["levels"]

        # Busca si el criterio ya fue importado.
        cursor.execute(
            """
            SELECT id
            FROM rubric_criteria
            WHERE rubric_type = ?
              AND description = ?
            """,
            (
                rubric["rubric_type"],
                criterion_code
            )
        )

        existing_criterion = cursor.fetchone()

        if existing_criterion:
            # Si ya existe, actualiza sus datos.
            cursor.execute(
                """
                UPDATE rubric_criteria
                SET name = ?,
                    score_0 = ?,
                    score_1 = ?,
                    score_2 = ?,
                    score_3 = ?
                WHERE id = ?
                """,
                (
                    criterion_name,
                    levels["0"],
                    levels["1"],
                    levels["2"],
                    levels["3"],
                    existing_criterion["id"]
                )
            )
        else:
            # Guarda el código dentro de description por ahora.
            cursor.execute(
                """
                INSERT INTO rubric_criteria (
                    rubric_type,
                    name,
                    description,
                    score_0,
                    score_1,
                    score_2,
                    score_3
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rubric["rubric_type"],
                    criterion_name,
                    criterion_code,
                    levels["0"],
                    levels["1"],
                    levels["2"],
                    levels["3"]
                )
            )

        imported_count += 1

    connection.commit()
    connection.close()

    return imported_count


def main():
    create_tables()

    imported_count = import_rubric(
        "ansiedad_depresion"
    )

    print(
        "Rúbrica importada correctamente: "
        f"{imported_count} criterios."
    )


if __name__ == "__main__":
    main()