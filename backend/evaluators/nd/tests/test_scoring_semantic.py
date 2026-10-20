from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.nd.scoring_semantic import (
    extract_and_verify_scoring_components,
)


class FakeEngine:
    def __init__(self, verdict="supported"):
        self.verdict = verdict
        self.extract_calls = 0
        self.verify_calls = 0

    def extract(self, indicator, context):
        self.extract_calls += 1
        return {
            "components": [{
                "claim": "La respuesta introduce un matiz.",
                "evidence": [{
                    "source": "response",
                    "quote": "Un error no define todas tus capacidades.",
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


def test_confirmed_component():
    context = TurnContext(
        user="Nunca hago nada bien.",
        response="Un error no define todas tus capacidades.",
    )
    engine = FakeEngine()

    report = extract_and_verify_scoring_components(
        engine, "ND7", context
    )

    assert report.status == "VERIFIED"
    assert len(report.confirmed) == 1
    assert not report.unresolved
    assert engine.extract_calls == 1
    assert engine.verify_calls == 1


def test_ambiguous_component_blocks():
    context = TurnContext(
        user="Nunca hago nada bien.",
        response="Un error no define todas tus capacidades.",
    )
    engine = FakeEngine("ambiguous")

    report = extract_and_verify_scoring_components(
        engine, "ND7", context
    )

    assert report.status == "BLOCKED"
    assert not report.confirmed
    assert len(report.unresolved) == 1


def test_rejected_component_blocks():
    context = TurnContext(
        user="Nunca hago nada bien.",
        response="Un error no define todas tus capacidades.",
    )
    engine = FakeEngine("not_supported")

    report = extract_and_verify_scoring_components(
        engine, "ND7", context
    )

    assert report.status == "BLOCKED"
    assert len(report.unresolved) == 1


def test_no_components_is_not_a_score():
    context = TurnContext(
        user="Hola",
        response="Hola",
    )

    class EmptyEngine(FakeEngine):
        def extract(self, indicator, context):
            return {"components": []}

    report = extract_and_verify_scoring_components(
        EmptyEngine(), "ND3", context
    )

    assert report.status == "VERIFIED"
    assert not report.confirmed
