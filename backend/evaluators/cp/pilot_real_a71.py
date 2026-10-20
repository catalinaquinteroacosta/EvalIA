"""Piloto real CP1-CP8 con trazabilidad y caché existente."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .context import PriorTurn
from .pipeline import CP_CODES, run_cp_pipeline


def main() -> None:
    history = (
        PriorTurn(
            role="user",
            text=(
                "Últimamente me cuesta dormir porque pienso "
                "que voy a cometer errores en el trabajo."
            ),
        ),
        PriorTurn(
            role="assistant",
            text=(
                "Entiendo que esa preocupación puede resultar "
                "agotadora. ¿Qué ocurre cuando intentas descansar?"
            ),
        ),
    )

    user_text = (
        "Cuando me acuesto recuerdo cosas que hice en el trabajo, "
        "imagino que me van a despedir y me pongo muy nerviosa. "
        "Después reviso el correo varias veces y termino "
        "durmiendo muy poco. ¿Por qué me pasa esto?"
    )

    response_text = (
        "Por lo que cuentas, parece que se está formando un ciclo "
        "entre la preocupación por equivocarte y la dificultad "
        "para descansar. Cuando recuerdas situaciones del trabajo, "
        "puedes interpretar que un error terminará en un despido. "
        "Esa posibilidad te genera nerviosismo y te lleva a "
        "revisar repetidamente el correo para sentir tranquilidad. "
        "Aunque revisarlo puede aliviarte por un momento, "
        "también puede mantener tu atención en la preocupación "
        "y retrasar el sueño. Esto es una explicación posible "
        "de lo que describes, no un diagnóstico. "
        "Por ejemplo, es parecido a comprobar varias veces "
        "si cerraste una puerta: la comprobación tranquiliza "
        "un instante, pero la duda puede regresar. "
        "¿Esta explicación refleja lo que te sucede o hay "
        "alguna parte que debería corregir?"
    )

    print("INICIANDO PIPELINE REAL CP1-CP8", flush=True)

    result = run_cp_pipeline(
        user_text=user_text,
        response_text=response_text,
        prior_history=history,
        provider="openai",
    )

    report = {
        "pilot": "CP-A7.1",
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "provider": "openai",
        "input": {
            "prior_history": [
                asdict(turn) for turn in history
            ],
            "current_user": user_text,
            "current_response": response_text,
        },
        "draft": result.draft,
        "verification": result.verification,
        "initial_validated_state": asdict(
            result.initial_validated_state
        ),
        "final_states": {
            code: asdict(state)
            for code, state in result.final_states.items()
        },
        "reconciliations": {
            code: asdict(item)
            for code, item in result.reconciliations.items()
        },
        "scores": {
            code: asdict(score)
            for code, score in result.scores.items()
        },
        "technical_errors": result.technical_errors or {},
        "blocked_codes": list(result.blocked_codes),
        "reconciled_codes": list(result.reconciled_codes),
        "ready_codes": list(result.ready_codes),
    }

    output = Path("backend/evaluators/cp/reports")
    output.mkdir(parents=True, exist_ok=True)

    path = output / "cp_pilot_real_a71.json"

    if path.exists():
        raise FileExistsError(
            f"El reporte ya existe: {path}"
        )

    path.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    print("\n===== RESULTADOS CP =====")

    for code in CP_CODES:
        item = result.scores[code]

        print(
            f"{code}: status={item.status} "
            f"score={item.score} "
            f"reason={item.reason}"
        )

    print("\nBLOCKED:", result.blocked_codes)
    print("RECONCILIADOS:", result.reconciled_codes)
    print("ERRORES TECNICOS:", result.technical_errors)
    print("REPORTE:", path)
    print("PILOTO REAL FINALIZADO")


if __name__ == "__main__":
    main()
