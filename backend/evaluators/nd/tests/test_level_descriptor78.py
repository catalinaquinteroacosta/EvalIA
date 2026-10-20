from backend.evaluators.nd.official_rubric import (
    load_official_nd_rubric,
)
from backend.evaluators.nd.level_semantic import (
    _one_level_analysis,
)
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


class FakeEngine:
    def __init__(self, descriptor):
        self.descriptor = descriptor
        self.saved = []

    def _run(self, *, stage, indicator, prompt, schema, inputs):
        return {
            "_uncached": {
                "level": "2",
                "descriptor": self.descriptor,
                "evidence_component_ids": [0],
                "verification": "supported",
                "reason": "Correspondencia semantica propuesta",
            },
            "_cache_key": stage,
        }

    def _commit(self, result, validated):
        self.saved.append(validated)
        return validated


def test_descriptor_is_loaded_from_official_rubric():
    context = TurnContext(
        user="Siempre fracaso.",
        response="Un error no define todos tus resultados.",
    )
    component = NDScoringComponent(
        indicator="ND7",
        claim="Introduce un matiz.",
        evidence=(
            Evidence(
                source="response",
                quote="Un error no define todos tus resultados.",
            ),
        ),
    )
    report = NDScoringEvidenceReport(
        indicator="ND7",
        confirmed=(component,),
        unresolved=(),
        status="VERIFIED",
    )

    engine = FakeEngine(
        "Texto diferente al descriptor oficial"
    )

    finding = _one_level_analysis(
        engine,
        "ND7",
        context,
        report,
        stage="level_extract",
    )

    expected = load_official_nd_rubric().levels["2"]

    assert finding.descriptor == expected
    assert engine.saved[0]["descriptor"] == expected
    assert finding.level == "2"
