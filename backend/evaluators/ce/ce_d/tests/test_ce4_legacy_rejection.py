
import pytest

from backend.evaluators.ce.ce_d.ce4_provider_bridge import (
    extract_ce4_draft,
)


@pytest.mark.parametrize("legacy_impact", [
    "functional",
    "secondary",
    "unusable",
    "substantial",
])
def test_legacy_structure_impact_cannot_replace_official_contract(
    legacy_impact,
):
    def legacy_runner(**kwargs):
        return {
            "analysis_complete": True,
            "full_response_audited": True,
            "applicable": True,
            "applicability_evidence": {
                "source": "response",
                "quote": "Hola",
                "interpretation": "Legacy test",
            },
            "structure_impact": legacy_impact,
            "claims": [{
                "source": "response",
                "quote": "Hola",
                "interpretation": "Legacy claim",
            }],
        }

    with pytest.raises(ValueError, match="Borrador incompleto"):
        extract_ce4_draft(
            user_text="Saludame",
            response_text="Hola",
            semantic_runner=legacy_runner,
        )
