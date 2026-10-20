from backend.evaluators.semantic.af_literal_markdown_recovery import (
    recover_markdown_literal,
)


def test_exact_quote():
    assert recover_markdown_literal(
        "Una frase original.",
        "frase original",
    ) == "frase original"


def test_markdown_quote():
    source = (
        "- **Hablar con alguien de confianza.** "
        "Compartir lo que sientes."
    )

    result = recover_markdown_literal(
        source,
        "Hablar con alguien de confianza. "
        "Compartir lo que sientes.",
    )

    assert result is not None
    assert result in source
    assert result == (
        "Hablar con alguien de confianza.** "
        "Compartir lo que sientes."
    )


def test_no_invented_content():
    assert recover_markdown_literal(
        "**Estudia** para el examen.",
        "Aprobaras el examen con seguridad.",
    ) is None


def test_no_changed_words():
    assert recover_markdown_literal(
        "**Estudia** para el examen.",
        "Estudia para todos los examenes.",
    ) is None


def test_no_cross_line_combination():
    assert recover_markdown_literal(
        "Primera frase.\nSegunda frase.",
        "Primera frase.Segunda frase.",
    ) is None
