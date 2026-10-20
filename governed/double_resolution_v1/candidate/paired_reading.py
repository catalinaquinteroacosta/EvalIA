"""Strict blind-reading contract, independent citations and source ownership."""
from backend.evaluators.nd.contracts import Evidence

def resolve(context, definitions, extraction, verification, *, conditional=False, user_gate=False, user_components=frozenset(), inactive_components=frozenset(), context_components=frozenset(),coverage_components=frozenset()):
    if not context.user.strip() or not context.response.strip():
        raise ValueError("Originales completos evaluables requeridos")
    readers=[]
    for reading in (extraction,verification):
        if set(reading)!={"components"}: raise ValueError("Salida ajena al contrato de componentes")
        rows=reading["components"]
        if not isinstance(rows,dict) or set(rows)-set(definitions): raise ValueError("Componentes desconocidos")
        readers.append(rows)
    required=set(definitions)
    if conditional and all(row.get("gate_present",{}).get("value") is False for row in readers):
        required={"gate_present"}
    values={}; evidence=[]
    for name in sorted(required):
        a,b=[row[name] for row in readers]
        inactive_null = name in inactive_components and a["value"] is None and b["value"] is None
        if not inactive_null and (type(a["value"]) is not bool or type(b["value"]) is not bool or a["value"]!=b["value"]):
            raise ValueError("Discrepancia o incertidumbre: "+name)
        for row in (a,b):
            if row["complete_response_reviewed"] is not True or not isinstance(row["reason"],str) or not row["reason"].strip():
                raise ValueError("Revisión completa o justificación ausente")
            own=tuple(Evidence(**e) for e in row["evidence"])
            contrary=tuple(Evidence(**e) for e in row["counterevidence"])
            if any(not e.verify_exact(context) for e in own+contrary): raise ValueError("Cita no literal")
            evidence.extend(own+contrary)
            if row["value"]:
                if not own and name not in coverage_components: raise ValueError("Afirmación sin evidencia propia del lector")
                if (name=="gate_present" and user_gate) or name in user_components:
                    if not any(e.source=="user" or (e.source=="history" and context.prior_history[e.history_index].role=="user") for e in own):
                        raise ValueError("Gate sin soporte propio del usuario/contexto causal")
                elif name!="gate_present" and name not in context_components and not any(e.source=="response" for e in own) and name not in coverage_components:
                    raise ValueError("Conducta de IA sin cita de respuesta actual")
        values[name]=a["value"]
    return values,tuple(evidence)
