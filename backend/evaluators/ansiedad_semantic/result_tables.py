"""Strict anxiety-only aggregation. Pending or BLOCKED suppress percentages."""
from collections import Counter
import csv
import json
from pathlib import Path

STATES = {"SCORED", "N/A", "BLOCKED", "PENDING"}

def validate(row):
    if row["status"] not in STATES:
        raise ValueError("Estado desconocido")
    number = row.get("score")
    if row["status"] == "SCORED":
        if type(number) is not int or number not in range(4):
            raise ValueError("Puntuación inválida")
        if row.get("applicability") != "APPLICABLE":
            raise ValueError("Puntuación sin aplicabilidad verificada")
    elif number is not None:
        raise ValueError("Estado sin puntuación contiene número")
    if row["status"] == "N/A":
        if row.get("applicability") != "NOT_APPLICABLE" or not row.get("gate_reason", "").strip():
            raise ValueError("N/A requiere gate oficial y justificación")
    return row

def aggregate(rows, *, expected_count=None):
    rows = [validate(row) for row in rows]
    identity_fields = ('conversation', 'model', 'turn', 'code')
    identities = [tuple(row[field] for field in identity_fields) for row in rows
                  if all(field in row for field in identity_fields)]
    if len(set(identities)) != len(identities):
        raise ValueError("Evaluación duplicada: no contar dos veces el mismo indicador/turno/modelo")
    counts = Counter(row["status"] for row in rows)
    complete = not counts["BLOCKED"] and not counts["PENDING"]
    if expected_count is not None:
        if type(expected_count) is not int or expected_count < len(rows):
            raise ValueError("Cantidad esperada inválida")
        complete = complete and len(rows) == expected_count
    scored = counts["SCORED"]
    points = sum(row["score"] for row in rows if row["status"] == "SCORED")
    return {"total": len(rows), "counts": {state: counts[state] for state in sorted(STATES)},
            "points": points, "scored_denominator": scored * 3,
            "complete": complete, "percentage": points / (scored * 3) * 100 if complete and scored else None,
            "percentage_method": "pooled_applicable_indicator_percentage",
            "percentage_scope": "Descriptive pooled score; not the V2 global mean of criterion percentages"}

def grouped(rows, fields):
    groups = {}
    for row in rows:
        key = tuple(row[field] for field in fields)
        groups.setdefault(key, []).append(row)
    return [{**dict(zip(fields, key)), **aggregate(values)} for key, values in sorted(groups.items())]

def export_new(directory, rows):
    """Exclusive writes preserve every historical artifact, including same path."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    rows = [validate(dict(row)) for row in rows]
    for name in ("observations.json", "observations.csv", "summary.json"):
        if (directory / name).exists():
            raise FileExistsError("No sobrescribir evidencia: " + str(directory / name))
    fields = sorted({key for row in rows for key in row})
    with (directory / "observations.json").open("x", encoding="utf-8") as out:
        json.dump(rows, out, ensure_ascii=False, indent=2)
    with (directory / "observations.csv").open("x", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict,list)) else value
                             for key,value in row.items()})
    with (directory / "summary.json").open("x", encoding="utf-8") as out:
        json.dump(aggregate(rows), out, ensure_ascii=False, indent=2)
