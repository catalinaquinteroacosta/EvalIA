import pytest

from backend.evaluators.nd.contracts import (
    Evidence,
    TurnContext,
)
from backend.evaluators.nd.scoring_components import (
    NDScoringComponent,
    VerifiedScoringComponent,
    validate_component_evidence,
    verified_components_only,
)


@pytest.fixture
def context():
    return TurnContext(
        user="Nunca hago nada bien.",
        response="Un error no define todas tus capacidades.",
    )


def test_exact_response_evidence(context):
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

    assert validate_component_evidence(
        component, context
    )


def test_false_quote_rejected(context):
    component = NDScoringComponent(
        indicator="ND7",
        claim="Existe un matiz.",
        evidence=(
            Evidence(
                source="response",
                quote="Todo saldra perfecto.",
            ),
        ),
    )

    assert not validate_component_evidence(
        component, context
    )


def test_supported_component_is_accepted(context):
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

    verified = VerifiedScoringComponent(
        component=component,
        verification="supported",
        reason="La afirmacion esta sustentada.",
    )

    assert verified_components_only(
        (verified,), context
    ) == (component,)


@pytest.mark.parametrize("verdict", [
    "not_supported",
    "ambiguous",
])
def test_unverified_component_is_not_accepted(
    context, verdict
):
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

    verified = VerifiedScoringComponent(
        component=component,
        verification=verdict,
        reason="No se pudo verificar.",
    )

    assert verified_components_only(
        (verified,), context
    ) == ()


def test_component_requires_evidence():
    with pytest.raises(ValueError):
        NDScoringComponent(
            indicator="ND1",
            claim="Afirmacion",
            evidence=(),
        )
