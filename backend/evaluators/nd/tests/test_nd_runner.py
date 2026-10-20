from backend.evaluators.nd.contracts import (
    ND_CODES,
    NDResult,
    TurnContext,
)
from backend.evaluators.nd.nd_runner import run_nd_family


def make_context():
    return TurnContext(
        user="Nunca hago nada bien.",
        response="Un error no define todas tus capacidades.",
    )


def test_runner_passes_same_engine(monkeypatch):
    calls = []
    engine = object()

    def fake_family(
        context,
        *,
        applicability_engine,
        level_resolver,
    ):
        assert applicability_engine is engine
        level_resolver("ND7", context)
        return ()

    def fake_resolver(received_engine, indicator, context):
        calls.append((received_engine, indicator))
        return object()

    monkeypatch.setattr(
        "backend.evaluators.nd.nd_runner.evaluate_nd_family",
        fake_family,
    )
    monkeypatch.setattr(
        "backend.evaluators.nd.nd_runner.resolve_safe_nd_level",
        fake_resolver,
    )

    result = run_nd_family(
        make_context(),
        engine=engine,
    )

    assert result == ()
    assert calls == [(engine, "ND7")]


def test_runner_preserves_family_results(monkeypatch):
    expected = tuple(
        NDResult(
            indicator=indicator,
            status="BLOCKED",
            score=None,
            reason="Prueba de aislamiento",
        )
        for indicator in ND_CODES
    )

    monkeypatch.setattr(
        "backend.evaluators.nd.nd_runner.evaluate_nd_family",
        lambda context, **kwargs: expected,
    )

    result = run_nd_family(
        make_context(),
        engine=object(),
    )

    assert result == expected
    assert len(result) == 8


def test_runner_does_not_construct_engine_when_provided(
    monkeypatch,
):
    def forbidden():
        raise AssertionError(
            "No se debe crear otro motor"
        )

    monkeypatch.setattr(
        "backend.evaluators.nd.nd_runner.NDSemanticEngine",
        forbidden,
    )
    monkeypatch.setattr(
        "backend.evaluators.nd.nd_runner.evaluate_nd_family",
        lambda context, **kwargs: (),
    )

    assert run_nd_family(
        make_context(),
        engine=object(),
    ) == ()
