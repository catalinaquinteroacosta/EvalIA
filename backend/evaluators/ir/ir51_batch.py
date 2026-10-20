
import json
import time
import traceback
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.evaluators.ir.core.contracts import Context, Message
from backend.evaluators.ir.core.component_engine import evaluate_components
from backend.evaluators.ir.core.level_engine import evaluate_level
from backend.evaluators.ir.core.scoring import score_indicator

ROOT = Path("backend/evaluators/ir")
REPORTS = ROOT / "reports/experiment072"
OUT = REPORTS / "ir51"
OUT.mkdir(parents=True, exist_ok=True)

CASES = json.loads(
    (ROOT / "fixtures/independent/ir_exp072_25_cases.json")
    .read_text(encoding="utf-8-sig")
)["cases"]

CODES = [f"IR{i}" for i in range(1, 8)]

if len(CASES) != 25 or len({c["case_id"] for c in CASES}) != 25:
    raise SystemExit("ERROR: fixture de 25 casos invalido.")

def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def save_new(path, value):
    # No reemplazar archivos existentes en OneDrive.
    with path.open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
    return read(path)

def context(case):
    return Context(
        user=case["user"],
        response=case["response"],
        prior_history=tuple(
            Message(role=m["role"], text=m["text"])
            for m in case["prior_history"]
        ),
    )

def initial_components(case, code):
    if case["case_id"] != "exp072_chatgpt_t01" or code != "IR1":
        return None

    sources = []
    for path in REPORTS.glob("ir46_*.json"):
        data = read(path)
        if (
            data.get("case_id") == case["case_id"]
            and data.get("indicator") == code
            and data.get("status") == "COMPONENTS_READY"
        ):
            sources.append(data)

    if len(sources) != 1:
        raise ValueError("IR46 ausente o duplicado.")

    return sources[0]["verified"]

def run_one(case, code):
    cid = case["case_id"]
    stem = f"{cid}_{code.lower()}"
    component_path = OUT / f"{stem}_components.json"
    level_path = OUT / f"{stem}_level.json"
    final_path = OUT / f"{stem}_final.json"

    if final_path.exists():
        final = read(final_path)
        return cid, code, final["status"], "REUTILIZADO"

    ctx = context(case)

    # Recuperar IR50 sin volver a consumir API.
    if cid == "exp072_chatgpt_t01" and code == "IR1":
        recovered = REPORTS / "ir50_chatgpt_t01_ir1_recovered.json"
        if recovered.exists():
            data = read(recovered)
            if (
                data.get("case_id") == cid
                and data.get("indicator") == code
                and data.get("status") == "SCORED"
                and data.get("level", {}).get("status") == "VERIFIED"
            ):
                final = {
                    "case_id": cid,
                    "indicator": code,
                    "status": data["status"],
                    "score": data["score"],
                    "level": data["level"],
                    "components": data["components"],
                    "source": "IR50",
                }
                save_new(final_path, final)
                return cid, code, "SCORED", "IR50"

    if component_path.exists():
        components = read(component_path)["components"]
    else:
        components = initial_components(case, code)
        if components is None:
            components = evaluate_components(ctx, code)

        save_new(component_path, {
            "case_id": cid,
            "indicator": code,
            "components": components,
        })

    if not isinstance(components, list):
        raise ValueError("Formato de componentes inesperado.")

    statuses = [x.get("status") for x in components]

    if not components or any(
        s not in ("supported", "absent_verified") for s in statuses
    ):
        final = {
            "case_id": cid,
            "indicator": code,
            "status": "BLOCKED",
            "reason": "Componentes pendientes de reconciliacion",
            "components": components,
        }
        save_new(final_path, final)
        return cid, code, "BLOCKED", "COMPONENTES"

    if level_path.exists():
        level = read(level_path)["level"]
    else:
        level = evaluate_level(ctx, code, components)
        save_new(level_path, {
            "case_id": cid,
            "indicator": code,
            "level": level,
        })

    if level.get("status") == "VERIFIED":
        score = score_indicator(
            code,
            applicability="applicable",
            verified_level=level["verified_level"],
            evidence_valid=level.get("evidence_valid", False),
        )
        status = score["status"]
    else:
        score = None
        status = "BLOCKED"

    final = {
        "case_id": cid,
        "indicator": code,
        "status": status,
        "score": score,
        "level": level,
        "components": components,
    }

    save_new(final_path, final)
    return cid, code, status, "NUEVO"

def main():
    tasks = [(case, code) for case in CASES for code in CODES]
    counts = {"SCORED": 0, "BLOCKED": 0, "ERROR": 0}
    errors = []

    print("IR51: INICIANDO", len(tasks), "EVALUACIONES", flush=True)
    print("TRABAJADORES: 3", flush=True)
    print("IR8: PENDIENTE APLICABILIDAD", flush=True)

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(run_one, case, code): (case["case_id"], code)
            for case, code in tasks
        }

        for index, future in enumerate(as_completed(futures), 1):
            cid, code = futures[future]

            try:
                _, _, status, origin = future.result()
                counts[status] = counts.get(status, 0) + 1
                detail = f"{status} ({origin})"
            except Exception as exc:
                counts["ERROR"] += 1
                detail = f"ERROR {type(exc).__name__}: {exc}"
                errors.append({
                    "case_id": cid,
                    "indicator": code,
                    "error": repr(exc),
                })

            print(
                f"[{index}/{len(tasks)}] {cid} {code}: {detail}",
                flush=True,
            )

    summary = {
        "total": len(tasks),
        "counts": counts,
        "errors": errors,
        "ir8": "PENDING_APPLICABILITY",
    }

    # Reporte nuevo; no sustituir reportes previos.
    name = f"ir51_summary_{time.time_ns()}.json"
    summary_path = OUT / name
    save_new(summary_path, summary)

    print("\n" + "=" * 55)
    print("IR51: RESUMEN")
    print("=" * 55)
    print("SCORED:", counts["SCORED"])
    print("BLOCKED:", counts["BLOCKED"])
    print("ERRORES TECNICOS:", counts["ERROR"])
    print("IR8: PENDIENTE")
    print("REPORTE:", summary_path)
    print("OTRAS FAMILIAS: SIN MODIFICACIONES")
    print("IR51 FINALIZADO")

if __name__ == "__main__":
    main()
