from database import get_connection, create_tables


def seed_ai_models(cursor):
    """Registra los modelos disponibles. No contiene escenarios."""
    models = [
        ("ChatGPT", "OpenAI"),
        ("Gemini", "Google"),
        ("Claude", "Anthropic"),
        ("Copilot", "Microsoft"),
        ("Perplexity", "Perplexity AI"),
    ]

    for name, provider in models:
        cursor.execute(
            """
            INSERT OR IGNORE INTO ai_models (name, provider)
            VALUES (?, ?)
            """,
            (name, provider),
        )


def main():
    create_tables()
    connection = get_connection()
    cursor = connection.cursor()

    try:
        seed_ai_models(cursor)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    print("Modelos iniciales de EvalIA cargados correctamente.")
    print(
        "Los escenarios se registran automáticamente desde "
        "database/prompts mediante backend/seed_turns.py."
    )


if __name__ == "__main__":
    main()
