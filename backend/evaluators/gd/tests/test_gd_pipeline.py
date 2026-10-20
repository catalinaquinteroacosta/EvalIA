from unittest.mock import patch

from backend.evaluators.gd.gd_pipeline import run_gd_pipeline
from backend.evaluators.gd.gd_schemas import GDContext, GDResult


def ctx():
    return GDContext(
        current_user="Necesito decidir.",
        current_response="Puedes valorar tus opciones.",
    )


def fake_results():
    return {
        f"GD{i}": GDResult(
            code=f"GD{i}",
            status="SCORED",
            score=3,
            reason="Verificación sintética.",
        )
        for i in range(1, 9)
    }


def run_mocked(component_status=None):
    statuses = component_status or {
        f"GD{i}": "VERIFIED" for i in range(1, 9)
    }

    with (
        patch(
            "backend.evaluators.gd.gd_pipeline.extract_gd",
            return_value={"indicators": []},
        ),
        patch(
            "backend.evaluators.gd.gd_pipeline.verify_gd",
            return_value={"verdicts": []},
        ),
        patch(
            "backend.evaluators.gd.gd_pipeline.verification_status",
            return_value=statuses,
        ),
        patch(
            "backend.evaluators.gd.gd_pipeline.review_gd_applicability",
            return_value=(),
        ),
        patch(
            "backend.evaluators.gd.gd_pipeline.reconcile_conditional_gd",
            return_value={
                "GD5": "APPLICABLE",
                "GD7": "APPLICABLE",
            },
        ),
        patch(
            "backend.evaluators.gd.gd_pipeline.classify_gd_levels",
            return_value={"indicators": []},
        ),
        patch(
            "backend.evaluators.gd.gd_pipeline.verify_gd_levels",
            return_value={"verdicts": []},
        ),
        patch(
            "backend.evaluators.gd.gd_pipeline.resolve_verified_levels",
            return_value=fake_results(),
        ),
    ):
        return run_gd_pipeline(ctx())


def test_all_eight_indicators():
    report = run_mocked()
    assert len(report.results) == 8
    assert all(
        x.status == "SCORED"
        for x in report.results.values()
    )


def test_one_component_disagreement_is_isolated():
    statuses = {
        f"GD{i}": "VERIFIED" for i in range(1, 9)
    }
    statuses["GD4"] = "BLOCKED"

    report = run_mocked(statuses)

    assert report.results["GD4"].status == "BLOCKED"
    assert report.results["GD4"].score is None
    assert report.results["GD3"].status == "SCORED"
    assert report.results["GD5"].status == "SCORED"


def test_missing_component_status_blocks():
    statuses = {
        f"GD{i}": "VERIFIED" for i in range(1, 9)
        if i != 6
    }

    report = run_mocked(statuses)

    assert report.results["GD6"].status == "BLOCKED"
    assert report.results["GD6"].score is None
