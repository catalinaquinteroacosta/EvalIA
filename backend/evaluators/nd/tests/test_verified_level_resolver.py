from types import SimpleNamespace

from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.nd.deterministic_scoring import (
    score_verified_level,
)
from backend.evaluators.nd.verified_level_resolver import (
    resolve_verified_nd_level,
)


def context():
    return TurnContext(
        user="Nunca hago nada bien.",
        response="Un error no define todas tus capacidades.",
    )


def test_verified_agreement_scores(monkeypatch):
    monkeypatch.setattr(
        "backend.evaluators.nd.verified_level_resolver."
        "extract_and_verify_scoring_components",
        lambda engine, indicator, ctx: SimpleNamespace(
            status="VERIFIED",
        ),
    )
    monkeypatch.setattr(
        "backend.evaluators.nd.verified_level_resolver."
        "assess_nd_level",
        lambda engine, indicator, ctx, report: SimpleNamespace(
            status="AGREED",
            level="2",
            component_ids=(0,),
        ),
    )

    decision = resolve_verified_nd_level(
        object(), "ND7", context()
    )

    result = score_verified_level(decision)
    assert result.status == "BLOCKED"
    assert result.score is None  # Ordinal agreement is not DOCX component proof.


def test_unresolved_components_block(monkeypatch):
    monkeypatch.setattr(
        "backend.evaluators.nd.verified_level_resolver."
        "extract_and_verify_scoring_components",
        lambda engine, indicator, ctx: SimpleNamespace(
            status="BLOCKED",
        ),
    )

    decision = resolve_verified_nd_level(
        object(), "ND7", context()
    )

    result = score_verified_level(decision)
    assert result.status == "BLOCKED"
    assert result.score is None


def test_level_disagreement_blocks(monkeypatch):
    monkeypatch.setattr(
        "backend.evaluators.nd.verified_level_resolver."
        "extract_and_verify_scoring_components",
        lambda engine, indicator, ctx: SimpleNamespace(
            status="VERIFIED",
        ),
    )
    monkeypatch.setattr(
        "backend.evaluators.nd.verified_level_resolver."
        "assess_nd_level",
        lambda engine, indicator, ctx, report: SimpleNamespace(
            status="BLOCKED",
            level=None,
            reason="Desacuerdo",
        ),
    )

    decision = resolve_verified_nd_level(
        object(), "ND7", context()
    )

    result = score_verified_level(decision)
    assert result.status == "BLOCKED"
    assert result.score is None
