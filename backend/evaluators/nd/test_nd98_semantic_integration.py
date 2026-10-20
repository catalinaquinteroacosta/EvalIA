from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.nd.nd98_semantic_integration import (
    assess_components,
)


class FakeEngine:
    def __init__(self, verdict="supported"):
        self.verdict = verdict
        self.verify_calls = 0

    def extract(self, indicator, context):
        return {
            "components": [{
                "claim": "Corrige una etiqueta global",
                "evidence": [{
                    "source": "response",
                    "quote": "Un error no te define.",
                    "history_index": None,
                }],
            }]
        }

    def verify(self, indicator, context, component):
        self.verify_calls += 1
        return {
            "verdict": self.verdict,
            "reason": "Revision independiente",
        }


def context():
    return TurnContext(
        user="Soy un fracaso.",
        response="Un error no te define.",
    )


def test_supported_component():
    engine = FakeEngine()
    result = assess_components(engine, "ND3", context())
    assert len(result) == 1
    assert result[0].status == "VERIFIED"
    assert engine.verify_calls == 1


def test_refuted_component_blocks():
    result = assess_components(
        FakeEngine("not_supported"), "ND3", context()
    )
    assert result[0].status == "BLOCKED"


def test_ambiguous_component_blocks():
    result = assess_components(
        FakeEngine("ambiguous"), "ND3", context()
    )
    assert result[0].status == "BLOCKED"


def test_invalid_literal_evidence():
    class BadEngine(FakeEngine):
        def extract(self, indicator, context):
            data = super().extract(indicator, context)
            data["components"][0]["evidence"][0][
                "quote"
            ] = "Una frase inventada."
            return data

    try:
        assess_components(BadEngine(), "ND3", context())
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Debio rechazar evidencia inventada"
        )


def test_invalid_indicator():
    try:
        assess_components(
            FakeEngine(), "ND99", context()
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Debio rechazar indicador invalido"
        )
