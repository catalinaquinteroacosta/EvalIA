"""Offline final evidence: execute joint tests and join the current live reports.

Does not call OpenAI, read credential files, or import the application backend.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from crisis_semantic.domain import ROOT, DOCS, load_contracts, digest
from crisis_semantic.predicate_catalog import definitions
from crisis_semantic.openai_private import PrivateStore


def main():
    contracts, manifest, common = load_contracts()
    folder = Path(__file__).resolve().parent
    runtime_files = {"domain.py", "pipeline.py", "predicate_catalog.py", "evidence.py", "openai_private.py", "scoring.py"}
    identity = digest({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.glob("*.py") if p.name in runtime_files or p.name.startswith("score_")})
    destination = DOCS / "delivery_2_8" / identity[:12]
    destination.mkdir(parents=True, exist_ok=True)
    commands = {
        "documentary_tests": ["node", "--test", "--test-reporter=tap", "tests/crisis_semantic/contracts.test.mjs"],
        "documentary_validation": ["node", "backend/evaluators/crisis_semantic/validate_contracts.mjs"],
        "python_tests": [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests/crisis_semantic", "-p", "test_*.py", "-v"],
        "scorer_generation_identity": [sys.executable, "-B", "backend/evaluators/crisis_semantic/pilot_cli.py", "build"],
    }
    runs = {}
    for name, command in commands.items():
        result = subprocess.run(command, cwd=ROOT, capture_output=True, encoding="utf-8", errors="replace")
        log = result.stdout + result.stderr
        (destination / (name + ".txt")).write_text(log, encoding="utf-8")
        runs[name] = {"command": command, "exit_code": result.returncode, "log": name + ".txt", "sha256": hashlib.sha256(log.encode()).hexdigest()}
        if name == "documentary_validation" and result.returncode == 0:
            runs[name]["result"] = json.loads(result.stdout)
    live_folder = DOCS / "live_pilot" / identity[:12]
    reports = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(live_folder.glob("*P*.json"))]
    rows = [r for out in reports for r in out["evaluation"]["results"]]
    checks = [c for out in reports for c in out["checks"]]
    families = {}
    for code, contract in contracts.items():
        relevant = [r for r in rows if r["code"] == code]
        entry = families.setdefault(contract["family_code"], {"implemented": 0, "attempted_codes": 0, "codes_with_score": 0, "codes_with_score_or_na": 0, "evaluations": 0, "statuses": Counter()})
        entry["implemented"] += 1
        entry["attempted_codes"] += bool(relevant)
        entry["codes_with_score"] += any(r["status"] == "SCORED" for r in relevant)
        entry["codes_with_score_or_na"] += any(r["status"] in ("SCORED", "N/A") for r in relevant)
        entry["evaluations"] += len(relevant)
        entry["statuses"].update(r["status"] for r in relevant)
    blocked = [{"case": out["case"], "package": out["package"], "code": r["code"], "cause": r["technical_cause"]} for out in reports for r in out["evaluation"]["results"] if r["status"] == "BLOCKED"]
    disagreements = [c for c in checks if not c["passed"]]
    trace = []
    for code, contract in contracts.items():
        short = code[3:].rstrip("0123456789").lower()
        trace.append({"code": code, "family": contract["family_code"], "official_question": contract["official_question"], "official_focus": contract["focus"], "official_gate": contract["applicability"], "official_levels": contract["levels"], "predicates": definitions(contracts, [code]), "function": "score_" + code[3:].lower(), "source_file": "backend/evaluators/crisis_semantic/score_" + short + ".py", "operationalization_review": "pending_documentary_review_not_clinically_validated"})
    (destination / "implementation_traceability.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
    inventory = []
    for relative in ("backend/evaluators/crisis_semantic", "tests/crisis_semantic", "docs/crisis_semantic"):
        for path in sorted((ROOT / relative).rglob("*")):
            if not path.is_file() or any(part in ("private_runtime", "private_pilot", "__pycache__") for part in path.parts):
                continue
            if destination in path.parents:
                continue
            data = path.read_bytes()
            inventory.append({"path": path.relative_to(ROOT).as_posix(), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    (destination / "files.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
    store = PrivateStore()
    with store.connect() as connection:
        cursor = connection.execute("SELECT id,stage,status,input_tokens,output_tokens,actual,committed,created FROM calls ORDER BY id")
        columns = [column[0] for column in cursor.description]
        calls = [dict(zip(columns, row)) for row in cursor.fetchall()]
    # Preserve nanodollar precision and distinguish actual estimates from reserves.
    for call in calls:
        actual = call.pop("actual")
        call["estimated_usd"] = None if actual is None else actual / 1e9
        call["committed_usd"] = call.pop("committed") / 1e9
    (destination / "api_calls.json").write_text(json.dumps(calls, indent=2), encoding="utf-8")
    summary = {"implementation_digest": identity, "source_sha256": manifest["source_sha256"], "implemented_indicators": len(contracts), "families": families, "local_runs": runs, "simulated_anchor_scenarios": 416,
               "live_cases": len({r["case"] for r in reports}), "live_package_batches": len(reports), "live_evaluations": len(rows), "live_statuses": dict(Counter(r["status"] for r in rows)), "live_checks_passed": sum(c["passed"] for c in checks), "live_checks_total": len(checks), "live_reference_status": "synthetic_documentary_hypotheses_not_clinical_gold_standard", "failed_checks": disagreements, "blocked_evaluations": blocked, "blocked_causes": dict(Counter(r["cause"] for r in blocked)), "never_resolved_codes": [c for c in contracts if not any(r["code"] == c and r["status"] in ("SCORED", "N/A") for r in rows)], "never_scored_codes": [c for c in contracts if not any(r["code"] == c and r["status"] == "SCORED" for r in rows)], "usage": PrivateStore().summary(), "clinical_validation": False, "complete_validation": False, "step_9_started": False,
               "acceptance": "DOCUMENTARY_PASS_AND_LOCAL_TECHNICAL_PASS; LIVE_PILOT_CONDITIONAL_PENDING_BLOCKS_AND_METHODOLOGY"}
    (destination / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    table = "\n".join(f'| {family} | {v["implemented"]} | {v["attempted_codes"]} | {v["statuses"].get("SCORED",0)} | {v["statuses"].get("N/A",0)} | {v["statuses"].get("BLOCKED",0)} |' for family, v in families.items())
    failures = "\n".join(f'- {v["code"]}: esperado documental {v["expected"]}; observado {v["actual"]}.' for v in disagreements) or "Ninguna discrepancia en las hipótesis documentales seleccionadas."
    causes = "\n".join(f'- {cause}: {count} evaluaciones.' for cause, count in summary["blocked_causes"].items()) or "Sin bloqueos en esta batería."
    report = f'''# Entrega técnica de los pasos 2 al 8

Implementados 104 contratos y 104 funciones Python explícitas en 10 familias. La API extrae y verifica componentes; Python decide la nota. Integración paso 9: no realizada. La validación completa NO se declara alcanzada: quedan revisión documental de operacionalizaciones, límites clínicos y bloqueos descritos aquí.

Fuente: SHA-256 `{manifest["source_sha256"]}`. Implementación: `{identity}`.

## Evidencia ejecutada

Pruebas locales: {", ".join(name + "=" + str(run["exit_code"]) for name, run in runs.items())} (0 significa aprobado). Los registros completos y sus hashes constan en [summary.json](summary.json). Los 416 escenarios cubren los cuatro niveles mediante componentes simulados; no demuestran exactitud semántica de 416 conversaciones reales.

API real: {summary["live_cases"]} casos sintéticos, {len(reports)} lotes, {len(rows)} evaluaciones; {summary["live_checks_passed"]}/{len(checks)} comprobaciones documentales coincidentes. La última ejecución reproduce observaciones reales válidas desde la caché privada, sin llamadas nuevas, aplicando las suspensiones técnicas RI2 y CE10. Estas referencias son hipótesis documentales, no adjudicación clínica profesional. Resultados por familia (los estados cuentan evaluaciones, no indicadores únicos):

| Familia | Implementados | Códigos intentados API | Con nota | N/A | BLOCKED |
|---|---:|---:|---:|---:|---:|
{table}

Los códigos únicos con nota o N/A se detallan por familia en summary.json. Los casos completos, citas, contraevidencias, decisiones del extractor y verificador ciego están en ../../live_pilot/{identity[:12]}/. No se utiliza conversación futura ni se mezclan modelos.

## Discrepancias reales pendientes

{failures}

## Bloqueos agrupados

{causes}

Inventario individual: summary.json → blocked_evaluations. No se convierten en 0 ni N/A. OP3/RI9 pueden requerir verificación externa que una cita literal y memoria del modelo no proporcionan. Desacuerdos independientes permanecen desconocidos cuando pueden cambiar la nota; un único lote de recuperación no fuerza consenso.

## Correcciones por causas comunes

- Fidelidad documental: tratamiento de saltos de página, tablas anidadas OP4 y campos no expresados; comparación independiente DOCX/.NET contra todos los campos.
- Salida API: esquema con propiedad obligatoria por predicado; índices nulos para citas actuales, enteros para historia; diagnóstico privado de salidas rechazadas. Se aumentó el techo de salida y se solicitaron citas y razones breves tras una respuesta truncada.
- Atribución: conducta de la respuesta separada del relato del usuario; una necesidad descrita por usuario no prueba conducta de la IA.
- Interpretación de riesgo/prioridad: invitación a relatar no se trata como pregunta de riesgo; ante incapacidad explícita de mantenerse a salvo no se acredita respiración antes de ayuda urgente como prioridad cumplida.
- Verificación: segunda lectura ciega, sin conclusiones del extractor. RI6 con orientación urgente y falso rescate simultáneos queda sin nota por frontera oficial no especificada, sin inventar un nivel.
- Regresión real RI2: la interpretación errónea de una invitación narrativa persistió aun con exclusiones expresas. Se suspende técnicamente la salida candidata de nivel 1 (BLOCKED sin nota); la función oficial conserva el nivel. [Fallo, alcance y condiciones para retirar la suspensión](../../LIVE_BLOCKS.md).
- Regresión real CE10: dos lectores no detectaron de forma fiable una contradicción explícita con el historial. Se suspende cualquier nota de CE10 cuando aplica; N/A y función oficial permanecen. La prueba 30 impide publicar esa nota hasta validar la comparación longitudinal.
- Fallos de conexión: se registran envíos impedidos antes de transmisión; resultados válidos se reutilizan. La caché y contabilidad son privadas, independientes de SQLite compartida.

## Pendientes y aceptación

[Pendientes del documento](../../methodological_pending.md) siguen abiertos. [Pendientes de implementación](../../PILOT_LIMITATIONS.md) distinguen decisiones técnicas, semánticas y clínicas. La descomposición en componentes es una operacionalización técnica para revisión: no se presenta como contenido literal adicional de la rúbrica ni como criterio clínico validado. Las pruebas simuladas comprueban ejecución y seguridad técnica, no sustituyen esa revisión. La ausencia de una nueva revisión por psicólogas durante el piloto no se interpreta como validación clínica.

Paso 2: integridad documental comprobada. Pasos 3–7: infraestructura y 104 evaluadores implementados y probados localmente; aceptación semántica condicionada por resultados reales y pendientes. Paso 8: piloto aislado ejecutable, con API real ya ensayada; no preparado para producción autónoma. Paso 9: no iniciado.

## Consumo y archivos

Costo estimado acumulado: US${summary["usage"]["estimated_cost_usd"]:.7f}; compromiso conservador US${summary["usage"]["committed_upper_bound_usd"]:.7f}; límite US$5. Tokens: {summary["usage"]["input_tokens"]} entrada, {summary["usage"]["output_tokens"]} salida. [Llamadas individuales, tokens, reservas y costos](api_calls.json); incluye los ensayos previos fallidos, no solo la última versión. Precio: [OpenAI GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini). No es factura del proveedor.

[Inventario con hashes](files.json), [trazabilidad implementación–rúbrica de los 104](implementation_traceability.json), [instrucciones de ejecución e integración futura](../../PILOT_USAGE.md). Todo el código y documentación del piloto está en las tres carpetas aisladas autorizadas. Runtime Python y caché privada se conservan bajo backend/evaluators/crisis_semantic; no se entregan ni copian credenciales. Los documentos del paso 2 son evidencia histórica de ese paso y no describen la ampliación posterior.
'''
    (destination / "REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"report": str(destination / "REPORT.md"), "live_checks": [summary["live_checks_passed"], len(checks)], "statuses": summary["live_statuses"], "usage": summary["usage"], "local_exit_codes": {k:v["exit_code"] for k,v in runs.items()}}, indent=2))
    return 1 if any(v["exit_code"] != 0 for v in runs.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
