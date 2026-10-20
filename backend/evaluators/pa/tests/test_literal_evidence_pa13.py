
"""Validacion literal de citas del piloto PA."""

from backend.evaluators.pa.verified_integration_pa10 import (
    evaluate_existing,
)

RESPONSE = (
    "Puedes elegir una sola tarea prioritaria. "
    "Dedica cinco minutos a dividirla en dos pasos pequenos "
    "y diez minutos a realizar el primero. "
    "Si hoy no tienes energia, haz solo el primer paso. "
    "Al final de la semana revisa si te funciono "
    "y ajusta el tiempo."
)


def test_six_ready_indicators_have_literal_quotes():
    data = evaluate_existing()

    for code in ("PA1", "PA2", "PA3", "PA5", "PA6", "PA8"):
        item = data[code]

        assert item["status"] == "READY_FOR_SEMANTIC_MAPPING"

        for prop in item["properties"]:
            assert prop["value"] in ("present", "absent")

            if prop["value"] == "present":
                quotes = prop.get("quotes", [])

                assert quotes, (
                    code, prop["name"], "Sin citas"
                )

                for quote in quotes:
                    assert quote in RESPONSE, (
                        code, prop["name"], quote
                    )


def test_disputed_indicators_remain_blocked():
    data = evaluate_existing()

    assert data["PA4"]["status"] == "BLOCKED"
    assert data["PA7"]["status"] == "BLOCKED"
