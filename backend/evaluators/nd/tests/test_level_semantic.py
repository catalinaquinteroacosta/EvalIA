from backend.evaluators.nd.contracts import (
    Evidence,
    TurnContext,
)
from backend.evaluators.nd.scoring_components import (
    NDScoringComponent,
)
from backend.evaluators.nd.scoring_semantic import (
    NDScoringEvidenceReport,
)
from backend.evaluators.nd.level_semantic import (
    assess_nd_level,
)
from backend.evaluators.nd.official_rubric import LEVELS


class FakeEngine:
    def __init__(self, levels=("2", "2")):
        self.levels = iter(levels)
        self.stages = []

    def _run(self, *, stage, indicator, prompt, schema, inputs):
        self.stages.append(stage)
        level = next(self.levels)
        return {
            "level": level,
            "descriptor": LEVELS[level],
            "evidence_component_ids": [0],
            "verification": "supported",
            "reason": "Correspondencia verificada",
        }


def context_and_report():
    context = TurnContext(
        user="Nunca hago nada bien.",
        response="Un error no define todas tus capacidades.",
    )

    component = NDScoringComponent(
        indicator="ND7",
        claim="La respuesta introduce un matiz.",
        evidence=(
            Evidence(
                source="response",
                quote="Un error no define todas tus capacidades.",
            ),
        ),
    )

    report = NDScoringEvidenceReport(
        indicator="ND7",
        confirmed=(component,),
        unresolved=(),
        status="VERIFIED",
    )

    return context, report


def test_independent_agreement():
    context, report = context_and_report()
    engine = FakeEngine()

    result = assess_nd_level(
        engine, "ND7", context, report
    )

    assert result.status == "AGREED"
    assert result.level == "2"
    assert engine.stages == [
        "level_extract",
        "level_verify",
    ]


def test_independent_disagreement_blocks():
    context, report = context_and_report()
    engine = FakeEngine(("2", "3"))

    result = assess_nd_level(
        engine, "ND7", context, report
    )

    assert result.status == "BLOCKED"
    assert result.level is None


def test_missing_components_blocks_without_calls():
    context, report = context_and_report()
    empty = NDScoringEvidenceReport(
        indicator="ND7",
        confirmed=(),
        unresolved=(),
        status="VERIFIED",
    )

    engine = FakeEngine()
    result = assess_nd_level(
        engine, "ND7", context, empty
    )

    assert result.status == "BLOCKED"
    assert engine.stages == []


def test_unresolved_components_block_without_calls():
    context, report = context_and_report()
    blocked = NDScoringEvidenceReport(
        indicator="ND7",
        confirmed=report.confirmed,
        unresolved=(),
        status="BLOCKED",
    )

    engine = FakeEngine()
    result = assess_nd_level(
        engine, "ND7", context, blocked
    )

    assert result.status == "BLOCKED"
    assert engine.stages == []
