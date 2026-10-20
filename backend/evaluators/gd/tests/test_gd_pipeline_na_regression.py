from unittest.mock import patch

from backend.evaluators.gd.gd_pipeline import run_gd_pipeline
from backend.evaluators.gd.gd_schemas import GDContext, GDResult


def run_case(applicability, component_status, results):
    context = GDContext(
        current_user="Necesito pensar qué hacer.",
        current_response="Puedes valorar tus alternativas.",
    )

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
            return_value=component_status,
        ),
        patch(
            "backend.evaluators.gd.gd_pipeline.review_gd_applicability",
            return_value=(),
        ),
        patch(
            "backend.evaluators.gd.gd_pipeline.reconcile_conditional_gd",
            return_value=applicability,
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
            return_value=results,
        ),
    ):
        return run_gd_pipeline(context)


def base_results():
    return {
        f"GD{i}": GDResult(
            code=f"GD{i}",
            status="SCORED",
            score=3,
            reason="Resultado sintético verificado.",
        )
        for i in range(1, 9)
    }


def base_status():
    return {
        f"GD{i}": "VERIFIED"
        for i in range(1, 9)
    }


def test_gd5_gd7_na_verified_not_overwritten():
    results = base_results()
    statuses = base_status()

    for code in ("GD5", "GD7"):
        results[code] = GDResult(
            code=code,
            status="NA",
            score=None,
            reason="Condición ausente y verificada.",
        )
        statuses[code] = "BLOCKED"

    report = run_case(
        {"GD5": "NA", "GD7": "NA"},
        statuses,
        results,
    )

    assert report.results["GD5"].status == "NA"
    assert report.results["GD7"].status == "NA"
    assert report.results["GD5"].score is None
    assert report.results["GD7"].score is None


def test_applicable_component_disagreement_blocks():
    results = base_results()
    statuses = base_status()
    statuses["GD5"] = "BLOCKED"

    report = run_case(
        {"GD5": "APPLICABLE", "GD7": "APPLICABLE"},
        statuses,
        results,
    )

    assert report.results["GD5"].status == "BLOCKED"
    assert report.results["GD5"].score is None
    assert report.results["GD4"].status == "SCORED"


def test_other_indicators_continue_when_one_blocks():
    results = base_results()
    statuses = base_status()
    statuses["GD3"] = "BLOCKED"

    report = run_case(
        {"GD5": "NA", "GD7": "NA"},
        statuses,
        results,
    )

    assert report.results["GD3"].status == "BLOCKED"
    assert report.results["GD1"].status == "SCORED"
    assert report.results["GD8"].status == "SCORED"
