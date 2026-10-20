
import argparse
import json
import traceback
from dataclasses import asdict
from pathlib import Path

from backend.evaluators.gd.gd_schemas import GDContext
from backend.evaluators.gd.gd_pipeline import run_gd_pipeline

ROOT = Path("backend/evaluators/gd")
FIXTURE = ROOT / "tests/fixtures/gd_contrast_cases_v2.json"
OUTPUT = ROOT / "reports/contrasts_v2"


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default="all")
    parser.add_argument("--retry-errors", action="store_true")
    args = parser.parse_args()

    cases = json.loads(FIXTURE.read_text(encoding="utf-8"))
    known = {case["id"] for case in cases}

    if args.case != "all" and args.case not in known:
        parser.error("Caso no encontrado.")

    for case in cases:
        case_id = case["id"]

        if args.case != "all" and args.case != case_id:
            continue

        destination = OUTPUT / f"{case_id}.json"

        if destination.exists():
            previous = json.loads(
                destination.read_text(encoding="utf-8")
            )
            if previous.get("execution_status") == "COMPLETED":
                print("REUTILIZADO:", case_id, flush=True)
                continue
            if not args.retry_errors:
                print("ERROR PREVIO, OMITIDO:", case_id, flush=True)
                continue

        print("EJECUTANDO:", case_id, flush=True)

        context = GDContext(
            current_user=case["current_user"],
            current_response=case["current_response"],
            prior_history=(),
        )

        record = {
            "case_id": case_id,
            "focus": case["focus"],
            "audit_question": case["audit_question"],
            "context": asdict(context),
        }

        try:
            report = run_gd_pipeline(
                context,
                provider="openai",
                use_cache=True,
            )

            record.update({
                "execution_status": "COMPLETED",
                "results": {
                    code: asdict(result)
                    for code, result in report.results.items()
                },
                "extraction": report.extraction,
                "component_verification": report.component_verification,
                "component_status": report.component_status,
                "applicability": report.applicability,
                "applicability_reviews": [
                    asdict(review)
                    for review in report.applicability_reviews
                ],
                "classification": report.classification,
                "level_verification": report.level_verification,
            })

            for code in case["focus"]:
                result = report.results[code]
                print(
                    f"  {code}: {result.status} "
                    f"score={result.score}",
                    flush=True,
                )

        except Exception:
            record["execution_status"] = "ERROR"
            record["traceback"] = traceback.format_exc()
            print("ERROR:", case_id, flush=True)

        save(destination, record)
        print("GUARDADO:", destination, flush=True)


if __name__ == "__main__":
    main()
