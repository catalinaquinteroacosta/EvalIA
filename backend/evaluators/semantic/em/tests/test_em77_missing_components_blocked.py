import pytest

from backend.evaluators.semantic.em.scorer import (
    UnresolvedScoringState,
    score_em13,
)


def test_em13_missing_components_never_invents_score():
    with pytest.raises(UnresolvedScoringState):
        score_em13(
            values={},
            applicability_reason="Indicador general",
        )


def test_em13_missing_components_not_converted_to_na():
    with pytest.raises(UnresolvedScoringState):
        score_em13(
            values={},
            applicability_reason="Contenido evaluable",
        )
