import pytest

from backend.evaluators.semantic.af_ai_af2_initiation import (
    AFAF2InitiationError,
    _validate_raw_result,
)


def test_perplexity_markdown():
    source = (
        "- **Respiraci?n lenta**: inhala por la nariz "
        "4 segundos, sost?n 4, exhala 6?8 segundos. "
        "Repite 3?5 minutos, especialmente antes "
        "de dormir o antes de estudiar. "
        "[fuente](https://example.org)"
    )

    result = _validate_raw_result(
        {
            "has_initiation": True,
            "initiation_description": (
                "Instrucciones para comenzar la respiraci?n"
            ),
            "quote": (
                "Respiraci?n lenta: inhala por la nariz "
                "4 segundos, sost?n 4, exhala 6?8 segundos. "
                "Repite 3?5 minutos, especialmente antes "
                "de dormir o antes de estudiar."
            ),
            "reason": "Contiene instrucciones concretas.",
        },
        current_ai=source,
    )

    assert result["quote"] in source
    assert "**" in result["quote"]


def test_rejects_invented_quote():
    with pytest.raises(AFAF2InitiationError):
        _validate_raw_result(
            {
                "has_initiation": True,
                "initiation_description": "Acci?n inventada",
                "quote": "El ?xito est? garantizado ma?ana.",
                "reason": "Prueba negativa.",
            },
            current_ai="Respira lentamente.",
        )
