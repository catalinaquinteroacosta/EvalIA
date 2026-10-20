
import argparse
import inspect
import json
import sys
import types
from dataclasses import asdict, is_dataclass
from pathlib import Path


ROOT = Path("backend/evaluators/cp")
WORK = ROOT / "reports/cp_a851_contrastive"


def serialize(value):
    if is_dataclass(value):
        return serialize(asdict(value))
    if isinstance(value, dict):
        return {
            str(k): serialize(v)
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [serialize(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (str, int, float, bool)):
        return value
    if value is None:
        return None
    raise TypeError(
        "Tipo de resultado no serializable: "
        + type(value).__name__
    )


def install_isolated_cache():
    path = Path(
        "backend/evaluators/semantic/semantic_cache.py"
    ).resolve()

    source = path.read_text(encoding="utf-8-sig")
    anchor = "semantic_cache = SemanticCache()"

    if source.count(anchor) != 1:
        raise RuntimeError(
            "No se pudo aislar la cache semantica."
        )

    cache = (
        WORK / "semantic_cache.sqlite3"
    ).resolve()

    WORK.mkdir(parents=True, exist_ok=True)

    name = (
        "backend.evaluators.semantic.semantic_cache"
    )

    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = (
        "backend.evaluators.semantic"
    )

    sys.modules[name] = module

    isolated = source.replace(
        anchor,
        "semantic_cache = SemanticCache(path="
        + repr(str(cache))
        + ")",
    )

    exec(
        compile(isolated, str(path), "exec"),
        module.__dict__,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--case",
        default="CP1-A",
    )
    args = parser.parse_args()

    cases_path = (
        ROOT
        / "reports/cp_a849_contrastive/cases.json"
    )

    cases = json.loads(
        cases_path.read_text(
            encoding="utf-8-sig"
        )
    )["cases"]

    case = next(
        (c for c in cases if c["id"] == args.case),
        None,
    )

    if case is None:
        raise ValueError(
            "Caso inexistente: " + args.case
        )

    WORK.mkdir(parents=True, exist_ok=True)

    output = WORK / (
        case["id"].lower().replace("-", "_")
        + "_result.json"
    )

    assert not output.exists(), (
        "Resultado existente. No sobrescribir."
    )

    install_isolated_cache()

    from backend.evaluators.cp.context import PriorTurn
    from backend.evaluators.cp.pipeline import (
        run_cp_pipeline,
    )

    history = tuple(
        PriorTurn(
            role=item["role"],
            text=item["text"],
        )
        for item in case["prior_history"]
    )

    signature = inspect.signature(
        run_cp_pipeline
    )

    kwargs = {
        "user_text": case["user"],
        "response_text": case["response"],
        "prior_history": history,
    }

    for key, value in {
        "timeout": 600,
        "extraction_max_output_tokens": 12000,
        "verification_max_output_tokens": 12000,
        "reconciliation_max_output_tokens": 12000,
    }.items():
        if key in signature.parameters:
            kwargs[key] = value

    print(
        "EJECUTANDO:",
        case["id"],
        flush=True,
    )

    print(
        "PIPELINE:",
        str(signature),
        flush=True,
    )

    result = run_cp_pipeline(**kwargs)

    payload = {
        "audit": "CP-A8.51",
        "step": "1/9",
        "rubric": "AD-02",
        "case": case,
        "result": serialize(result),
        "contrastive_acceptance_completed": False,
    }

    output.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("RESULTADO:", output)
    print("TIPO:", type(result).__name__)
    print("EJECUCION COMPLETADA")


if __name__ == "__main__":
    main()
