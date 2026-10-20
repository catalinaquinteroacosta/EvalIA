
import argparse
import json
import hashlib
import os
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .contracts import HistoryMessage, Turn
from .runner import audit_result
from .openai_adapter import OpenAIJSON
from .runner import RECONCILE_SYSTEM, _merge_reconciliation
from .semantic import evaluate_one


ROOT = Path(__file__).parent
DOSSIER = ROOT / "reports/ps23_v3_reconciliation_dossier.json"
OUTPUT = ROOT / "reports/ps23_v3_reconciliation_causal_v2.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument(
        "--model",
        default=os.environ.get("EVALIA_PS_MODEL", "gpt-4o-mini"),
    )
    args = parser.parse_args()

    dossier = json.loads(DOSSIER.read_text(encoding="utf-8"))
    cases = [
        item for item in dossier["cases"]
        if not (
            item["case_id"] == "urgent"
            and item["indicator"] == "PS3"
        )
    ]

    # PS23_SAFE_LIVE_V1
    identity = hashlib.sha256(
        json.dumps(
            {
                "dossier": dossier,
                "system": RECONCILE_SYSTEM,
                "model": args.model,
            },
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()

    # PS23_CAUSAL_V2
    causal_instruction = (
        ROOT / "ps23_causal_reconciliation_instruction.txt"
    ).read_text(encoding="utf-8")

    causal_system = (
        RECONCILE_SYSTEM
        + "\n\n"
        + causal_instruction
    )

    identity = hashlib.sha256(
        json.dumps(
            {
                "previous_identity": identity,
                "causal_instruction": causal_instruction,
                "model": args.model,
            },
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()

    response_dir = ROOT / ".cache" / "ps23_v3_responses" / identity


    if not args.live:
        print(json.dumps({
            "mode": "DRY_RUN",
            "cases": len(cases),
            "api_calls": 0,
            "model": args.model,
            "output": str(OUTPUT),
        }, ensure_ascii=False, indent=2))
        return 0

    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY no configurada.")

    response_dir.mkdir(parents=True, exist_ok=True)

    if OUTPUT.exists():
        existing = json.loads(OUTPUT.read_text(encoding="utf-8"))
        if existing.get("family") != "PS":
            raise SystemExit("Reporte existente incompatible.")
        if existing.get("model") != args.model:
            raise SystemExit("Modelo diferente al reporte existente.")
        if existing.get("identity") != identity:
            raise SystemExit("Identidad del expediente diferente.")
        results = existing.get("cases", [])
        if not isinstance(results, list):
            raise SystemExit("Reporte existente inv?lido.")
    else:
        results = []

    from openai import OpenAI

    client = OpenAI(timeout=45, max_retries=1)
    adapter = OpenAIJSON(client, args.model)

    completed = {
        (r["case_id"], r["indicator"])
        for r in results
    }

    for item in cases:
        if (item["case_id"], item["indicator"]) in completed:
            print(
                "REUTILIZADO:",
                item["case_id"],
                item["indicator"],
                flush=True,
            )
            continue
        code = item["indicator"]
        context = item["turn"]

        turn = Turn(
            context["user"],
            context["response"],
            tuple(
                HistoryMessage(**message)
                for message in context["prior_history"]
            ),
        )

        original_extract = item["original_extraction"]
        original_verify = item["original_verification"]
        reason = item["original_decision"]["reason"]

        payload = {
            "indicator": code,
            "user": turn.user,
            "response": turn.response,
            "prior_history": [
                asdict(message) for message in turn.prior_history
            ],
            "extraction": original_extract,
            "previous_verification": original_verify,
            "blocked_reason": reason,
            "official_rubric": item["official_rubric"],
        }

        response_file = response_dir / (
            f"{item['case_id']}_{code}.json"
        )

        if response_file.exists():
            proposed = json.loads(
                response_file.read_text(encoding="utf-8")
            )
            print("RESPUESTA REUTILIZADA:", item["case_id"], code)
        else:
            proposed = adapter(causal_system, payload)

            temporary_response = response_file.with_suffix(".tmp")
            temporary_response.write_text(
                json.dumps(proposed, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temporary_response.replace(response_file)


        # PS23_VALIDATED_REUSE_V1
        if not isinstance(proposed, dict):
            raise ValueError(
                f"Respuesta de reconciliaci?n inv?lida: {item['case_id']}/{code}"
            )
        if proposed.get("indicator") != code:
            raise ValueError(
                f"Indicador incompatible: {item['case_id']}/{code}"
            )
        if reason in (
            "Applicability unverified",
            "Applicability not resolved",
        ):
            if not isinstance(proposed.get("applicability"), dict):
                raise ValueError(
                    "Falta aplicabilidad reconciliada."
                )

        elif reason in (
            "Rubric level not uniquely supported",
            "Unverified or malformed level proposition",
        ):
            if not isinstance(proposed.get("levels"), dict):
                raise ValueError(
                    "Faltan niveles reconciliados."
                )

        else:
            raise ValueError(
                "Motivo de reconciliaci?n no autorizado: "
                + str(reason)
            )

        # PS23_CAUSAL_CHECKPOINT_V6
        causal_error = None

        if reason in (
            "Applicability unverified",
            "Applicability not resolved",
        ):
            applicability = proposed.get("applicability", {})

            if not isinstance(applicability, dict):
                causal_error = "Aplicabilidad invalida."
            else:
                for field in ("evidence", "counterevidence"):
                    items = applicability.get(field, [])

                    if not isinstance(items, list):
                        causal_error = "Lista de evidencia invalida."
                        break

                    for evidence in items:
                        if not isinstance(evidence, dict):
                            causal_error = "Evidencia malformada."
                            break

                        if evidence.get("source") == "response":
                            causal_error = (
                                "Applicability contaminated "
                                "by CURRENT_RESPONSE"
                            )
                            break

                    if causal_error:
                        break

        if causal_error:
            from .contracts import Decision

            decision = Decision(
                indicator=code,
                score=None,
                status="BLOCKED",
                reason=causal_error,
            )

            results.append({
                "case_id": item["case_id"],
                "indicator": code,
                "final_decision": asdict(decision),
                "causal_rejection": causal_error,
                "proposed_reconciliation": proposed,
            })

            checkpoint = {
                "family": "PS",
                "model": args.model,
                "identity": identity,
                "created_utc": datetime.now(
                    timezone.utc
                ).isoformat(),
                "cases": results,
            }

            temporary = OUTPUT.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(
                    checkpoint,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            temporary.replace(OUTPUT)

            print(
                item["case_id"],
                code,
                "BLOCKED",
                causal_error,
                flush=True,
            )
            continue

        merged = _merge_reconciliation(
            original_verify, proposed, reason
        )

        result = evaluate_one(
            turn,
            code,
            lambda system, payload: deepcopy(original_extract),
            lambda system, payload: deepcopy(merged),
        )

        decision = result.decision

        if decision.status in ("NA", "SCORED"):
            findings = audit_result(turn, result)
            if findings:
                from .contracts import Decision
                decision = Decision(
                    code,
                    None,
                    "BLOCKED",
                    "Evidence audit failed: " + repr(findings),
                )

        results.append({
            "case_id": item["case_id"],
            "indicator": code,
            "original_decision": item["original_decision"],
            "proposed_verification": proposed,
            "merged_verification": merged,
            "final_decision": asdict(decision),
        })

        checkpoint = {
            "family": "PS",
            "model": args.model,
            "identity": identity,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "cases": results,
        }

        temporary = OUTPUT.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(checkpoint, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(OUTPUT)

        print(
            item["case_id"],
            code,
            decision.status,
            decision.score,
            flush=True,
        )

    OUTPUT.write_text(
        json.dumps({
            "family": "PS",
            "model": args.model,
            "created_utc": datetime.now(
                timezone.utc
            ).isoformat(),
            "cases": results,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("REPORTE:", OUTPUT)
    print("CASOS:", len(results))
    print(
        "BLOCKED:",
        sum(
            x["final_decision"]["status"] == "BLOCKED"
            for x in results
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
