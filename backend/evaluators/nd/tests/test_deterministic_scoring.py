import pytest

from backend.evaluators.nd.deterministic_scoring import (
    VerifiedLevel,
    score_verified_level,
    score_family_verified,
)


@pytest.mark.parametrize("level,score", [
    ("0", 0),
    ("1", 1),
    ("2", 2),
    ("3", 3),
])
def test_ordinal_labels_cannot_replace_individual_docx_components(level, score):
    decision = VerifiedLevel(
        indicator="ND7",
        level=level,
        extraction_verdict="supported",
        independent_verdict="supported",
        reason="Componente semanticamente verificado",
    )
    result = score_verified_level(decision)
    assert result.status == "BLOCKED"
    assert result.score is None


@pytest.mark.parametrize("verdict", [
    "not_supported",
    "ambiguous",
])
def test_independent_rejection_blocks(verdict):
    decision = VerifiedLevel(
        indicator="ND7",
        level="3",
        extraction_verdict="supported",
        independent_verdict=verdict,
        reason="Discrepancia",
    )
    result = score_verified_level(decision)
    assert result.status == "BLOCKED"
    assert result.score is None


def test_extraction_rejection_blocks():
    decision = VerifiedLevel(
        indicator="ND1",
        level="0",
        extraction_verdict="not_supported",
        independent_verdict="supported",
        reason="Extraccion sin respaldo",
    )
    assert score_verified_level(decision).status == "BLOCKED"


def test_complete_family():
    decisions = tuple(
        VerifiedLevel(
            indicator=f"ND{i}",
            level="2",
            extraction_verdict="supported",
            independent_verdict="supported",
            reason="Validado",
        )
        for i in range(1, 9)
    )
    results = score_family_verified(decisions)
    assert len(results) == 8
    assert results[0].indicator == "ND1"
    assert results[0].status == "BLOCKED" and results[0].score is None
    assert all(result.status == "BLOCKED" and result.score is None for result in results)
    # Generic AD-04 ordinal agreements are historical evidence, not DOCX proof.


def test_duplicate_indicator_rejected():
    decisions = tuple(
        VerifiedLevel(
            indicator="ND1",
            level="1",
            extraction_verdict="supported",
            independent_verdict="supported",
            reason="Validado",
        )
        for _ in range(8)
    )
    with pytest.raises(ValueError):
        score_family_verified(decisions)


def test_invalid_level_rejected():
    with pytest.raises(ValueError):
        VerifiedLevel(
            indicator="ND7",
            level="4",
            extraction_verdict="supported",
            independent_verdict="supported",
            reason="Nivel inexistente",
        )
