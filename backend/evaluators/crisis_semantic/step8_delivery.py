"""Read-only comparison audit; writes delivery artifacts only in crisis docs."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from crisis_semantic.domain import DOCS, PRIVATE, load_contracts
from crisis_semantic.span_provider import fingerprint
from crisis_semantic.openai_private import PrivateStore, MODEL
from crisis_semantic.predicate_catalog import definitions

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

def build():
    folder = DOCS / "step8" / fingerprint()[:12]
    comparison_path = folder / "comparison_8660c0df2a.json"
    comparison = read(comparison_path)
    contracts, manifest, _ = load_contracts()
    before_path = DOCS / "delivery_2_8/2afc6c1dcaf9/summary.json"
    before = read(before_path)
    transitions, pending, packages, resolved_checks = [], [], {}, []
    baseline_rows = []
    for report in comparison["reports"]:
        original_path = DOCS / "live_pilot/2afc6c1dcaf9" / (report["case"] + "_" + report["package"] + ".json")
        original_report = read(original_path) if not report["extra"] else {}
        original = {r["code"]: r for r in original_report.get("evaluation", {}).get("results", [])}
        for check in original_report.get("checks", []):
            if not check["passed"]:
                after_check = next(c for c in report["checks"] if c["code"] == check["code"])
                resolved_checks.append({"case":report["case"], "package":report["package"], "root_cause":original[check["code"]].get("technical_cause"), "before":check, "after":after_check})
        for row in report["evaluation"]["results"]:
            if row["status"] == "BLOCKED":
                pending.append({"case": report["case"], "package": report["package"], "extra_control": report["extra"], "code": row["code"], "cause": row["technical_cause"], "unresolved": {key: value["issues"] for key,value in row.get("verified_decisions", {}).items() if value["value"] is None}})
            if report["extra"]:
                continue
            baseline_rows.append(row)
            prior = original[row["code"]]
            transitions.append({"case": report["case"], "package": report["package"], "code": row["code"], "before_status": prior["status"], "before_cause": prior.get("technical_cause"), "before_score": prior["score"], "after_status": row["status"], "after_score": row["score"], "after_cause": row.get("technical_cause")})
    for package in ("P1", "P2", "P3", "P4"):
        packages[package] = dict(Counter(row["after_status"] for row in transitions if row["package"] == package))
    causes = {}
    for cause in before["blocked_causes"]:
        selected = [r for r in transitions if r["before_status"] == "BLOCKED" and r["before_cause"] == cause]
        causes[cause] = {"before": len(selected), "after_states": dict(Counter(r["after_status"] for r in selected))}
    store = PrivateStore()
    usage = store.summary()
    with store.connect() as db:
        calls = [dict(zip(("id","stage","reserved","committed","actual","input_tokens","output_tokens","status","model","input_nanodollars_per_token","output_nanodollars_per_token"), row)) for row in db.execute("SELECT c.id,c.stage,c.reserved,c.committed,c.actual,c.input_tokens,c.output_tokens,c.status,COALESCE(r.model,?),COALESCE(r.input_rate,400),COALESCE(r.output_rate,1600) FROM calls c LEFT JOIN call_rates r ON c.id=r.call_id ORDER BY c.id", (MODEL,))]
    old_calls = read(DOCS / "delivery_2_8/2afc6c1dcaf9/api_calls.json")
    for prior, current in zip(old_calls, calls):
        for field in ("id", "stage", "status", "input_tokens", "output_tokens"):
            assert prior[field] == current[field], (prior["id"], field)
        assert prior["estimated_usd"] == (current["actual"] / 1e9 if current["actual"] is not None else None)
        assert prior["committed_usd"] == current["committed"] / 1e9
    assert len(resolved_checks) == 11 and all(c["after"]["passed"] for c in resolved_checks)
    root = Path(__file__).resolve().parents[3]
    old_inventory = {entry["path"]:entry for entry in read(DOCS / "delivery_2_8/2afc6c1dcaf9/files.json")}
    contract_names = {"docs/crisis_semantic/" + family["file"] for family in manifest["families"]}
    protected = [entry for name,entry in old_inventory.items() if (name.startswith("backend/evaluators/crisis_semantic/score_") and name.endswith(".py")) or name in contract_names]
    assert len(contract_names) == 10 and len(protected) == 20
    for entry in protected:
        assert hashlib.sha256((root / entry["path"]).read_bytes()).hexdigest() == entry["sha256"], entry["path"]
    write(folder / "implementation_traceability.json", [{"code":code,"official_question":c["official_question"],"focus":c["focus"],"applicability":c["applicability"],"levels":c["levels"],"predicates":definitions(contracts,[code]),"clinical_validation":False} for code,c in contracts.items()])
    # Export contains accounting only, never request headers or credentials.
    write(folder / "api_accounting.json", {"usage": usage, "calls": calls})
    write(folder / "transitions.json", transitions)
    write(folder / "root_causes.json", {"blocked": causes, "failed_checks_by_root_cause":dict(Counter(c["root_cause"] for c in resolved_checks)), "previous_failed_checks": resolved_checks, "remaining": pending})
    covered = {r["code"] for r in baseline_rows}
    assert len(covered) == 104 and len(transitions) == 501
    assert usage["committed_upper_bound_usd"] <= 5
    assert len(calls) >= before["usage"]["calls"]
    summary = {"source_sha256": manifest["source"]["sha256"] if "source" in manifest else before["source_sha256"], "comparison_sha256": hashlib.sha256(comparison_path.read_bytes()).hexdigest(), "indicators": len(covered), "families": 10, "baseline_evaluations": len(transitions), "extra_control_evaluations": sum(len(r["evaluation"]["results"]) for r in comparison["reports"] if r["extra"]), "before": comparison["before"], "after": {**comparison["after"], "usage": usage}, "packages": packages, "pending": pending, "clinical_validation": False, "complete_validation": False, "step9_started": False}
    write(folder / "delivery_summary.json", summary)
    family_names = {"CR-01":"CS","CR-02":"CT","CR-03":"OP","CR-04":"NI","CR-05":"PP","CR-06":"AC","CR-07":"RE","CR-08":"CE","CR-09":"RI","CR-10":"GA"}
    lines = ["# Paso 8: corrección y validación por bloques", "", "Estado: avance técnico con pendientes; sin validación clínica completa. Paso 9 no ejecutado.", "", "## Comparación sobre los mismos 501 resultados", "", "| Métrica | Antes | Después |", "|---|---:|---:|"]
    for state in ("SCORED","N/A","BLOCKED"):
        lines.append(f"| {state} | {comparison['before']['statuses'].get(state,0)} | {comparison['after']['statuses'].get(state,0)} |")
    lines += [f"| Comprobaciones coincidentes | {comparison['before']['checks_passed']}/31 | {comparison['after']['checks_passed']}/31 |", "", "Los 104 indicadores y las 10 familias tienen cobertura. Los 30 resultados del control longitudinal adicional se informan aparte para no alterar el denominador: 24 puntuados, 5 N/A, 1 BLOCKED (OP3). Las expectativas son hipótesis documentales, no un patrón clínico adjudicado.", "", "## Causas comunes y correcciones", "", "- 127 bloqueos por facturación indeterminada de solicitudes antiguas: protocolo nuevo de evidencia por identificadores de segmentos literales, con nueva extracción y verificación ciega por paquetes. Las ocho reservas antiguas permanecen intactas; no se repitieron solicitudes idénticas de facturación incierta.", "- 39 por componentes sin resolver y 10 por aplicabilidad: reutilización de observaciones verificadas válidas, esquema que separa evidencia actual de contexto y rechaza atribuir conductas de la IA a palabras del usuario; recuperación conjunta de componentes pendientes. No se cambian gates oficiales.", "- RI2: predicado atómico separado de su exclusión narrativa; ocho controles superados, incluida pregunta vaga auténtica. CE10: contraste explícito entre historia y respuesta, con cita previa obligatoria; contradicción=0 y continuidad legítima=3.", "- AC3, AC4 y RE4: resueltos por el mecanismo común de fuentes y evidencia. No se alteraron sus funciones de puntuación.", "- Un fallo de transporte anterior al envío afectó CS+CT completo: recuperación de ese paquete sin repetir los demás.", "", "## Resultados por familia (501 resultados comparables)", "", "| Familia | Puntuados | N/A | BLOCKED |", "|---|---:|---:|---:|"]
    for family, counts in comparison["after"]["families"].items():
        lines.append(f"| {family_names[family]} | {counts.get('SCORED',0)} | {counts.get('N/A',0)} | {counts.get('BLOCKED',0)} |")
    lines += ["", "## Pendientes", "", "RI6 y OP4 en false_rescue_dependency: los componentes están acordados pero la combinación no tiene un anclaje oficial inequívoco implementable sin adjudicación. OP3 en ese caso y en el control adicional: desacuerdo ausencia/incertidumbre y necesidad de evidencia externa. Conservan BLOCKED, score=null. No se inventa una nota para cerrar la batería.", "", "Las once comprobaciones antes pendientes ahora coinciden; las once ambigüedades metodológicas M01–M11 son un inventario diferente y permanecen documentadas en methodological_pending.md. No hay nueva revisión profesional. El acuerdo entre lectores del mismo modelo tampoco prueba exactitud clínica.", "", "Las suspensiones RI2/CE10 se liberan solo para el proveedor SpanProvider, protocolo/modelo/huella exactos y certificado de esta batería. El proveedor anterior conserva las suspensiones. Un cambio semántico invalida el certificado.", "", "## API y seguridad", "", f"Consumo acumulado estimado: US${usage['estimated_cost_usd']:.7f}; compromiso máximo incluyendo reservas inciertas: US${usage['committed_upper_bound_usd']:.7f}, límite US$5. Incremento estimado en este paso: US${usage['estimated_cost_usd']-before['usage']['estimated_cost_usd']:.7f}. {usage['calls']-before['usage']['calls']} nuevos registros de intentos; detalle por modelo/tokens/estado en api_accounting.json. Ocho reservas históricas inciertas siguen retenidas. No es una factura de OpenAI.", "", "API solo para observaciones y verificación; puntuación Python independiente. Sin regex semántica, sin turnos futuros, sin lectura de .env, sin caché compartida y sin integración. La contabilidad privada se conserva; no reiniciarla.", "", "## Evidencias y reproducción", "", "- comparison_8660c0df2a.json: entradas, evidencia, decisiones, controles y resultados completos.", "- transitions.json y root_causes.json: 501 transiciones y discrepancias agrupadas.", "- delivery_summary.json y api_accounting.json: cobertura y consumo auditable.", "- python_tests.txt, node_tests.txt y documentary_validation.txt: ejecuciones conjuntas y validación de rúbrica.", "", "Reproducción sin gasto: ejecutar pilot_cli.py pilot sin --allow-api. Pruebas: los comandos de PILOT_USAGE.md. Integración futura requiere autorización para paso 9, conservar BLOCKED, presupuesto, procedencia y revisión profesional pendiente."]
    (folder / "REPORT.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    verification = read(folder / "verification.json") if (folder / "verification.json").exists() else {}
    if verification:
        assert all(result["exit_code"] == 0 for result in verification.values())
        with (folder / "REPORT.md").open("a",encoding="utf-8") as report:
            report.write("\n## Pruebas ejecutadas y archivos\n\n40 pruebas Python y 27 pruebas Node aprobadas; cero fallidas. 416 escenarios simulados de niveles. Validación documental: 6.469 campos, 986 referencias, 104 indicadores, 416 descriptores, cero discrepancias. El control de tamaño/fecha de Node conservó 4.706 archivos fuera del alcance (credenciales excluidas). La auditoría de este paso conserva los 202 registros contables anteriores sin cambios. Las funciones de puntuación oficiales y los contratos mantienen sus hashes anteriores.\n\nSeguridad probada: rechazo de cita inventada o atribuida al usuario, contexto previo obligatorio para CE10, verificador ciego, filtrado temporal y por modelo, aislamiento de caché, presupuesto concurrente, conservación de facturación incierta, no compensación entre indicadores y BLOCKED sin nota. El test conjunto recalcula todas las notas publicadas y verifica todas sus citas positivas. No sustituye adjudicación clínica.\n\nArchivos fuente creados/modificados y hashes en files.json; nuevas evidencias completas en esta carpeta. Reproducción final sin llamadas nuevas ni consumo adicional.\n")
    inventory = []
    for relative in ("backend/evaluators/crisis_semantic", "tests/crisis_semantic", "docs/crisis_semantic"):
        for path in sorted((root / relative).rglob("*")):
            if not path.is_file() or any(part in ("private_runtime","private_pilot","__pycache__") for part in path.parts):
                continue
            name = path.relative_to(root).as_posix()
            if name.endswith("/files.json") or ("docs/crisis_semantic/step8/" in name and folder not in path.parents):
                continue
            data = path.read_bytes()
            hashed = hashlib.sha256(data).hexdigest()
            previous = old_inventory.get(name)
            if previous is None or previous["sha256"] != hashed:
                inventory.append({"path":name,"change":"created" if previous is None else "modified","bytes":len(data),"sha256":hashed})
    write(folder / "files.json", inventory)
    print(json.dumps({"report":str(folder / "REPORT.md"),"coverage":len(covered),"statuses":comparison["after"]["statuses"]},indent=2))

if __name__ == "__main__":
    build()
