"""IR-03: ejecutor semántico, sin scoring."""

import json
import sys
from dataclasses import asdict

from .core.contracts import Context, Message
from .core.semantic import INDICATORS, extract
from .core.verify import verify


def run(ctx):
    extracted = extract(ctx)
    result = {}
    for indicator in INDICATORS:
        claims = verify(
            ctx, indicator, extracted[indicator]
        )
        blocked = any(
            c["verification"] == "ambiguous"
            for c in claims
        )
        result[indicator] = {
            "status": "BLOCKED" if blocked else "EXTRACTED",
            "claims": claims,
            "score": None,
        }
    return {
        "family": "IR",
        "stage": "semantic_unscored",
        "indicators": result,
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit(
            "Uso: python -m backend.evaluators.ir.runner archivo.json"
        )
    with open(sys.argv[1], encoding="utf-8") as f:
        raw = json.load(f)
    ctx = Context(
        user=raw["user"],
        response=raw["response"],
        prior_history=tuple(
            Message(**m)
            for m in raw.get("prior_history", [])
        ),
    )
    print(json.dumps(run(ctx), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()