"""Pruebas de cierre: auditoria y decision CE1."""

from unittest.mock import patch

import pytest

from backend.evaluators.ce.ce_a import (
    ce1_integrated,
    ce1_final_decision,
)


def extraction():
    return {
        "primary_need": "Preparar una entrevista",
        "explicit_needs": [{
            "interpretation": "Preparar una entrevista",
            "user_evidence": "Ayudame con mi entrevista",
        }],
        "contextual_needs": [],
        "ce1_relevant_evidence": [],
        "ce1_digressions": [],
        "ce2_essential_information_present": [],
        "ce2_essential_omissions": [],
        "ce2_unnecessary_overload": [],
    }


def audit(verdict, field=None):
    return {
        "verdict": verdict,
        "findings": (
            [{
                "field": field,
                "issue": "Componente faltante",
                "evidence": "Ayudame con mi entrevista",
            }]
            if field else []
        ),
        "reason": "Comprobacion de cobertura.",
    }


@pytest.mark.parametrize(
    "field",
    [
        "primary_need",
        "explicit_needs",
        "contextual_needs",
        "ce1_relevant_evidence",
        "ce1_digressions",
    ],
)
def test_ce1_missing_component_stops_integration(
    field,
):
    with (
        patch.object(
            ce1_integrated,
            "audit_coverage",
            return_value=audit("incomplete", field),
        ),
        patch.object(
            ce1_integrated,
            "build_ce1_need_inventory",
        ) as inventory,
    ):
        result = ce1_integrated.evaluate_ce1_integrated(
            user_text="Ayudame con mi entrevista",
            response_text="Practica tus respuestas.",
            extraction=extraction(),
        )

    assert result["status"] != "evidence_integrated"
    assert result["score"] is None
    inventory.assert_not_called()


def test_ambiguous_audit_stops_integration():
    with (
        patch.object(
            ce1_integrated,
            "audit_coverage",
            return_value=audit("ambiguous"),
        ),
        patch.object(
            ce1_integrated,
            "build_ce1_need_inventory",
        ) as inventory,
    ):
        result = ce1_integrated.evaluate_ce1_integrated(
            user_text="Ayudame con mi entrevista",
            response_text="Practica tus respuestas.",
            extraction=extraction(),
        )

    assert result["status"] != "evidence_integrated"
    inventory.assert_not_called()


@pytest.mark.parametrize(
    "field",
    [
        "ce2_essential_information_present",
        "ce2_essential_omissions",
        "ce2_unnecessary_overload",
    ],
)
def test_ce2_only_finding_passes_ce1_gate(
    field,
):
    # Detenemos la ejecucion justo despues del
    # filtro para demostrar que CE1 lo supero.
    class GatePassed(Exception):
        pass

    with (
        patch.object(
            ce1_integrated,
            "audit_coverage",
            return_value=audit("incomplete", field),
        ),
        patch.object(
            ce1_integrated,
            "build_ce1_need_inventory",
            side_effect=GatePassed,
        ),
    ):
        with pytest.raises(GatePassed):
            ce1_integrated.evaluate_ce1_integrated(
                user_text="Ayudame con mi entrevista",
                response_text="Practica tus respuestas.",
                extraction=extraction(),
            )


def test_incomplete_integration_cannot_score():
    with (
        patch.object(
            ce1_final_decision,
            "evaluate_ce1_integrated",
            return_value={
                "status": "review_required",
                "primary_coverage": None,
            },
        ),
        patch.object(
            ce1_final_decision,
            "classify_ce1_relevance",
        ) as classifier,
    ):
        result = ce1_final_decision.decide_ce1(
            user_text="Ayudame con mi entrevista",
            response_text="Practica tus respuestas.",
        )

    assert result["score"] is None
    classifier.assert_not_called()


def test_maximum_requires_complete_relevance():
    integrated = {
        "status": "evidence_integrated",
        "primary_need": "Preparar una entrevista",
        "primary_coverage": "addressed",
        "fragments": [],
    }

    classification = {
        "primary_relevance": "partially_related",
        "total_deviation": False,
        "issues": [],
        "analysis_complete": True,
    }

    with (
        patch.object(
            ce1_final_decision,
            "evaluate_ce1_integrated",
            return_value=integrated,
        ),
        patch.object(
            ce1_final_decision,
            "classify_ce1_relevance",
            return_value=classification,
        ),
    ):
        result = ce1_final_decision.decide_ce1(
            user_text="Ayudame con mi entrevista",
            response_text="Practica tus respuestas.",
        )

    assert result["score"] is None
