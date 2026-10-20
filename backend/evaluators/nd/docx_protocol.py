"""Blind, component-only paired reading of ND2–ND8 originals."""
from dataclasses import asdict
import json
from .contracts import Evidence, NDResult
from .nd1_official import ComponentReview
from .docx_components import contracts, definitions, score

def prompt(code, cases, stage):
    if stage not in ("extract", "independent_verify"):
        raise ValueError("Etapa desconocida")
    return json.dumps({
        "stage": stage, "indicator": code,
        "instruction": "Examina originales completos y contraevidencia. No devuelvas notas ni elijas niveles. Reporta componentes true/false/null y citas literales; null ante incertidumbre técnica. El verificador trabaja sin conclusiones del extractor. No atribuyas al asistente frases del usuario. No uses turnos futuros.",
        "official_construct": contracts()[code]["official_heading"],
        "official_applicability": contracts()[code]["applicability_literal"],
        "components": definitions(code),
        "cases": {key: asdict(context) for key, context in cases.items()},
        "output": "cases: id -> components: name -> {value: bool|null, evidence: [{source,quote,history_index}], counterevidence: [...], complete_response_reviewed: bool, reason: str}",
    }, ensure_ascii=False)

def adjudicate(code, cases, extraction, verification):
    results = {}
    for key, context in cases.items():
        try:
            readers = [reader["cases"][key]["components"] for reader in (extraction, verification)]
            required = set(definitions(code))
            # A nonactivated conditional gate needs no merit adjudication.
            if all(reader.get("gate_present", {}).get("value") is False for reader in readers):
                required = {"gate_present"}
            if any(set(reader) - set(definitions(code)) for reader in readers):
                raise ValueError("Componente desconocido")
            reviews = []
            for name in sorted(required):
                a, b = [reader[name] for reader in readers]
                for row in (a, b):
                    if not isinstance(row.get("reason"), str) or not row["reason"].strip():
                        raise ValueError("Cada lector debe justificar contextualmente cada componente")
                    if row["value"] is True:
                        evidence = tuple(Evidence(**e) for e in row["evidence"])
                        if not evidence or any(not e.verify_exact(context) for e in evidence):
                            raise ValueError("Cada lector debe aportar evidencia literal propia")
                        if name == "gate_present" and not any(e.source == "user" or (e.source == "history" and context.prior_history[e.history_index].role == "user") for e in evidence):
                            raise ValueError("Cada lector debe acreditar el gate con contexto del usuario")
                        if name != "gate_present" and not any(e.source == "response" for e in evidence):
                            raise ValueError("Conducta sin cita propia de IA")
                reviews.append(ComponentReview(name, a["value"], b["value"],
                    tuple(Evidence(**e) for row in (a,b) for e in row["evidence"]),
                    tuple(Evidence(**e) for row in (a,b) for e in row["counterevidence"]),
                    all(row["complete_response_reviewed"] is True for row in (a,b)),
                    a["reason"] + " | " + b["reason"]))
            results[key] = score(code, context, tuple(reviews))
        except (KeyError, TypeError, ValueError, IndexError) as error:
            results[key] = NDResult(code, "BLOCKED", None, "Protocolo inválido: " + str(error))
    return results
