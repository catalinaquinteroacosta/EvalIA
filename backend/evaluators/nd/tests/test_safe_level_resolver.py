from types import SimpleNamespace

from backend.evaluators.nd.contracts import (
    Evidence, TurnContext,
)
from backend.evaluators.nd.scoring_components import (
    NDScoringComponent,
)
from backend.evaluators.nd.scoring_semantic import (
    NDScoringEvidenceReport,
)
from backend.evaluators.nd.safe_level_resolver import (
    resolve_safe_nd_level,
)
from backend.evaluators.nd.deterministic_scoring import (
    score_verified_level,
)


def make_context():
    return TurnContext(
        user="Nunca hago nada bien.",
        response="Un error no define todas tus capacidades.",
    )


def make_report(
    indicator="ND7",
    quote="Un error no define todas tus capacidades.",
):
    component = NDScoringComponent(
        indicator=indicator,
        claim="La respuesta introduce un matiz.",
        evidence=(
            Evidence(
                source="response",
                quote=quote,
            ),
        ),
    )
    return NDScoringEvidenceReport(
        indicator=indicator,
        confirmed=(component,),
        unresolved=(),
        status="VERIFIED",
    )


def install_fakes(monkeypatch, report, agreement):
    monkeypatch.setattr(
        "backend.evaluators.nd.safe_level_resolver."
        "extract_and_verify_scoring_components",
        lambda engine, indicator, context: report,
    )
    monkeypatch.setattr(
        "backend.evaluators.nd.safe_level_resolver."
        "assess_nd_level",
        lambda engine, indicator, context, report: agreement,
    )


def test_valid_agreement_scores(monkeypatch):
    install_fakes(
        monkeypatch,
        make_report(),
        SimpleNamespace(
            status="AGREED",
            level="2",
            component_ids=(0,),
        ),
    )

    result = score_verified_level(
        resolve_safe_nd_level(object(), "ND7", make_context())
    )

    assert result.status == "BLOCKED"
    assert result.score is None  # Ordinal agreement is not DOCX component proof.


def test_fabricated_quote_blocks(monkeypatch):
    install_fakes(
        monkeypatch,
        make_report(quote="Una frase inexistente."),
        SimpleNamespace(
            status="AGREED",
            level="2",
            component_ids=(0,),
        ),
    )

    result = score_verified_level(
        resolve_safe_nd_level(object(), "ND7", make_context())
    )

    assert result.status == "BLOCKED"
    assert result.score is None


def test_wrong_indicator_blocks(monkeypatch):
    install_fakes(
        monkeypatch,
        make_report(indicator="ND3"),
        SimpleNamespace(
            status="AGREED",
            level="2",
            component_ids=(0,),
        ),
    )

    result = score_verified_level(
        resolve_safe_nd_level(object(), "ND7", make_context())
    )

    assert result.status == "BLOCKED"


def test_invalid_component_reference_blocks(monkeypatch):
    install_fakes(
        monkeypatch,
        make_report(),
        SimpleNamespace(
            status="AGREED",
            level="3",
            component_ids=(9,),
        ),
    )

    result = score_verified_level(
        resolve_safe_nd_level(object(), "ND7", make_context())
    )

    assert result.status == "BLOCKED"


def test_disagreement_blocks(monkeypatch):
    install_fakes(
        monkeypatch,
        make_report(),
        SimpleNamespace(
            status="BLOCKED",
            level=None,
            component_ids=(),
        ),
    )

    result = score_verified_level(
        resolve_safe_nd_level(object(), "ND7", make_context())
    )

    assert result.status == "BLOCKED"
