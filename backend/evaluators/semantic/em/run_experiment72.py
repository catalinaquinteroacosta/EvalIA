
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from backend.evaluators.semantic.em.pipeline_v2 import (
    evaluate_em_indicator_v2,
)
from backend.evaluators.semantic.em.extractor_v2 import (
    EM_EXTRACTOR_V2_VERSION,
)
from backend.evaluators.semantic.em.verifier_v2 import (
    EM_VERIFIER_V2_VERSION,
)
from backend.evaluators.semantic.em.scorer import (
    EM_SCORER_VERSION,
)
from backend.evaluators.semantic.em.pipeline_v2 import (
    EM_PIPELINE_V2_VERSION,
)
from backend.evaluators.semantic.semantic_provider import (
    get_semantic_identity,
)


BASE = Path("backend/evaluators/semantic/em/reports")
DATASET = BASE / "experiment72_dataset.json"
OUTPUT = BASE / "experiment72_em_results.jsonl"

CODES = tuple(f"EM{i}" for i in range(1, 14))


def canonical(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def identity(record, code):
    provider = get_semantic_identity()

    payload = {
        "record": record,
        "indicator": code,
        "provider": provider,
        "extractor_version": EM_EXTRACTOR_V2_VERSION,
        "verifier_version": EM_VERIFIER_V2_VERSION,
        "scorer_version": EM_SCORER_VERSION,
        "pipeline_version": EM_PIPELINE_V2_VERSION,
        "applicability_input": "true",
    }

    return hashlib.sha256(
        canonical(payload).encode("utf-8")
    ).hexdigest()


def load_completed():
    completed = {}

    if not OUTPUT.exists():
        return completed

    for line in OUTPUT.read_text(
        encoding="utf-8"
    ).splitlines():
        if not line.strip():
            continue

        item = json.loads(line)

        if item.get("result", {}).get("status") == "ok":
            completed[item["identity"]] = item

    return completed


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--limit",
        type=int,
        default=1,
    )

    args = parser.parse_args()

    records = json.loads(
        DATASET.read_text(encoding="utf-8")
    )

    assert len(records) == 25

    selected = records[:args.limit]

    completed = load_completed()

    BASE.mkdir(parents=True, exist_ok=True)

    total = len(selected) * len(CODES)
    processed = 0

    for record in selected:
        for code in CODES:
            key = identity(record, code)

            if key in completed:
                processed += 1
                print(
                    "REUSED",
                    record["model"],
                    record["turn"],
                    code,
                    flush=True,
                )
                continue

            print(
                "EVALUATING",
                record["model"],
                record["turn"],
                code,
                f"{processed + 1}/{total}",
                flush=True,
            )

            try:
                result = evaluate_em_indicator_v2(
                    code,
                    user_message=record["user_message"],
                    ai_response=record["ai_response"],
                    prior_history=record["prior_history"],
                    evaluable_emotional_or_experiential_content="true",
                )
            except Exception as exc:
                result = {
                    "indicator_code": code,
                    "status": "error",
                    "applicable": None,
                    "score": None,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }

            entry = {
                "identity": key,
                "experiment": 72,
                "model_evaluated": record["model"],
                "turn": record["turn"],
                "indicator": code,
                "result": result,
            }

            with OUTPUT.open(
                "a",
                encoding="utf-8",
            ) as handle:
                handle.write(
                    canonical(entry) + "\n"
                )
                handle.flush()

            processed += 1

            print(
                "RESULT",
                record["model"],
                record["turn"],
                code,
                "STATUS",
                result.get("status"),
                "SCORE",
                result.get("score"),
                flush=True,
            )

    print()
    print("RUN COMPLETE:", processed, "/", total)
    print("REPORT:", OUTPUT)


if __name__ == "__main__":
    main()
