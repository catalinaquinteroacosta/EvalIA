"""Run from this file without importing the main backend or global registry."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "evaluate", "pilot", "usage"))
    parser.add_argument("--input", type=Path)
    parser.add_argument("--allow-api", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cases", nargs="*")
    args = parser.parse_args()
    if args.command == "build":
        from crisis_semantic.build_scorers import build
        print(json.dumps(build()))
        return
    from crisis_semantic.openai_private import OpenAIPrivate, PrivateStore
    if args.command == "usage":
        print(json.dumps(PrivateStore().summary(), indent=2))
        return
    if args.command == "pilot":
        from crisis_semantic.closure_replay import run
        result = run(args.cases)
        print(json.dumps({'replay_only':True,'new_api_calls':0,'statuses':result['statuses']},indent=2))
    else:
        from crisis_semantic.span_provider import SpanProvider
        provider = SpanProvider(allow_api=args.allow_api)
        if args.input is None:
            parser.error("--input required")
        from crisis_semantic.domain import Turn, Input, load_contracts
        from crisis_semantic.pipeline import CrisisEvaluator
        data = json.loads(args.input.read_text(encoding="utf-8"))
        context = Input.from_conversation([Turn(**t) for t in data["turns"]], data["turn_number"], data["model"])
        contracts, _, _ = load_contracts()
        result = CrisisEvaluator(provider).evaluate(context, data.get("codes", list(contracts)))
    if args.output:
        from crisis_semantic.domain import DOCS, PRIVATE
        target = args.output.resolve()
        if not (target.is_relative_to(DOCS) or target.is_relative_to(PRIVATE)):
            parser.error("output must be in isolated crisis docs/private folders")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps({"completed": True, "usage": PrivateStore().summary()}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
