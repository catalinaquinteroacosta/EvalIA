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
    _one_level_analysis,
)
from backend.evaluators.nd.official_rubric import LEVELS


def fixture():
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


class FakeCachedEngine:
    def __init__(self, verification="supported"):
        self.verification = verification
        self.cache = {}
        self.calls = []
        self.commits = 0

    def _run(self, *, stage, indicator, prompt, schema, inputs):
        self.calls.append(stage)
        if stage in self.cache:
            return self.cache[stage]

        return {
            "_uncached": {
                "level": "2",
                "descriptor": LEVELS["2"],
                "evidence_component_ids": [0],
                "verification": self.verification,
                "reason": "Revision independiente",
            },
            "_cache_key": stage,
        }

    def _commit(self, result, validated):
        self.commits += 1
        if "_uncached" in result:
            self.cache[result["_cache_key"]] = validated
        return validated


def test_supported_level_is_cached():
    context, report = fixture()
    engine = FakeCachedEngine()

    first = _one_level_analysis(
        engine, "ND7", context, report,
        stage="level_extract",
    )
    second = _one_level_analysis(
        engine, "ND7", context, report,
        stage="level_extract",
    )

    assert first == second
    assert engine.commits == 1
    assert len(engine.cache) == 1


def test_independent_stages_have_separate_cache():
    context, report = fixture()
    engine = FakeCachedEngine()

    _one_level_analysis(
        engine, "ND7", context, report,
        stage="level_extract",
    )
    _one_level_analysis(
        engine, "ND7", context, report,
        stage="level_verify",
    )

    assert set(engine.cache) == {
        "level_extract",
        "level_verify",
    }


def test_ambiguous_level_is_not_cached():
    context, report = fixture()
    engine = FakeCachedEngine("ambiguous")

    _one_level_analysis(
        engine, "ND7", context, report,
        stage="level_extract",
    )

    assert engine.commits == 0
    assert engine.cache == {}


def test_rejected_level_is_not_cached():
    context, report = fixture()
    engine = FakeCachedEngine("not_supported")

    _one_level_analysis(
        engine, "ND7", context, report,
        stage="level_verify",
    )

    assert engine.commits == 0
    assert engine.cache == {}
