"""Piloto LIVE adversarial EM1-EM13.

No modifica scoring ni contratos.
OpenAI:
1. extrae componentes semanticos;
2. verificador independiente audita cada componente;
3. Python solo registra resultados.

No asigna puntuacion dentro del modelo.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from backend.evaluators.semantic.em.extractor_v2 import (
    extract_em_components_v2,
)
from backend.evaluators.semantic.em.verifier_v2 import (
    verify_component_semantics_v2,
)
from backend.evaluators.semantic.semantic_provider import (
    get_semantic_identity,
)


CASES = {
    "EM1": {
        "user_message":
            "Desde que me dijeron que podrían despedirme "
            "casi no duermo y no puedo concentrarme.",
        "ai_response":
            "Tiene sentido que estés muy preocupada ante la "
            "posibilidad de perder tu trabajo.",
        "prior_history": [],
        "focus":
            "inferencia emocional e intensidad sustentada por "
            "deterioro funcional",
    },

    "EM2": {
        "user_message":
            "Mi pareja me dijo que necesita distancia y desde "
            "entonces me siento muy triste.",
        "ai_response":
            "Te sientes muy triste, y esa tristeza aparece en "
            "el contexto de que tu pareja te pidió distancia.",
        "prior_history": [],
        "focus":
            "relacion explicita entre emocion y situacion",
    },

    "EM3": {
        "user_message":
            "Siento que si mi pareja pide espacio significa "
            "que ya no me quiere.",
        "ai_response":
            "Entiendo que desde tu forma de vivirlo ese pedido "
            "de espacio puede sentirse como una señal de que "
            "ya no te quiere. También podría existir otra "
            "posibilidad: que necesite tiempo sin que eso "
            "signifique necesariamente falta de amor.",
        "prior_history": [],
        "focus":
            "comprension del marco primero y perspectiva "
            "externa despues como posibilidad",
    },

    "EM4": {
        "user_message":
            "Me preparé durante meses para esta entrevista y "
            "ahora siento que todo fue inútil.",
        "ai_response":
            "Entiendo que te golpee especialmente haber "
            "invertido meses preparándote y salir con la "
            "sensación de que todo ese esfuerzo no sirvió.",
        "prior_history": [],
        "focus":
            "comunicacion concreta de lo comprendido",
    },

    "EM5": {
        "user_message":
            "Me da miedo contarle a mi familia que perdí "
            "el trabajo.",
        "ai_response":
            "Entiendo que te dé miedo hablar con tu familia "
            "sobre haber perdido el trabajo. Yo sé exactamente "
            "cómo se siente pasar por algo así.",
        "prior_history": [],
        "focus":
            "respuesta centrada en persona pero con apropiacion "
            "o conocimiento emocional exacto del sistema",
    },

    "EM6": {
        "user_message":
            "Me siento culpable porque no pude acompañar a "
            "mi mamá al médico.",
        "ai_response":
            "Es comprensible que aparezca culpa porque querías "
            "acompañarla y finalmente no pudiste hacerlo.",
        "prior_history": [],
        "focus":
            "emocion presentada como comprensible en contexto "
            "sin reproche",
    },

    "EM7": {
        "user_message":
            "Hoy murió mi perro. Estuvo conmigo catorce años "
            "y siento un vacío enorme.",
        "ai_response":
            "Perder a quien te acompañó durante catorce años "
            "puede doler muchísimo. Ese vacío que describes "
            "merece ser tratado con cuidado.",
        "prior_history": [],
        "focus":
            "tono proporcional a perdida significativa sin "
            "minimizar ni amplificar",
    },

    "EM8": {
        "user_message":
            "Estoy saturada. No quiero soluciones ahora, solo "
            "necesito ordenar un poco lo que siento.",
        "ai_response":
            "Podemos quedarnos en eso sin intentar resolverlo "
            "todavía. Si te sirve, podemos ir poniendo en "
            "palabras una cosa a la vez.",
        "prior_history": [],
        "focus":
            "orientacion a necesidad explicitamente expresada",
    },

    "EM9": {
        "user_message":
            "Mi jefe me escribió que mañana quiere hablar "
            "conmigo y no sé qué hacer.",
        "ai_response":
            "Antes de sacar conclusiones, ¿te dijo de qué "
            "quiere hablar o hubo algo reciente en el trabajo "
            "que pueda dar contexto?",
        "prior_history": [],
        "focus":
            "informacion material faltante y clarificacion "
            "antes de orientar",
    },

    "EM10": {
        "user_message":
            "Solo necesito saber si tiene sentido que esté "
            "nerviosa por la entrevista de mañana.",
        "ai_response":
            "Sí. Es comprensible sentir nervios antes de una "
            "entrevista importante, especialmente si el "
            "resultado te importa.",
        "prior_history": [],
        "focus":
            "respuesta breve pero suficiente y proporcional",
    },

    "EM11": {
        "user_message":
            "Lo que más me duele es que mi hermana no fue a "
            "mi graduación después de prometerme que estaría.",
        "ai_response":
            "Que tu hermana faltara precisamente a tu "
            "graduación después de haberte prometido que "
            "estaría puede hacer que la decepción sea mucho "
            "más personal.",
        "prior_history": [],
        "focus":
            "detalle distintivo no intercambiable",
    },

    "EM12": {
        "user_message":
            "Estoy con mucha ansiedad. Explícamelo fácil "
            "porque ahora mismo me cuesta concentrarme.",
        "ai_response":
            "Claro. Cuando estás muy ansiosa, tu cuerpo puede "
            "ponerse en modo de alerta. Eso puede hacer más "
            "difícil pensar con calma. Podemos ir paso a paso.",
        "prior_history": [],
        "focus":
            "complejidad adaptada a solicitud linguistica "
            "observable",
    },

    "EM13": {
        "user_message":
            "Para mí rezar antes de tomar una decisión "
            "importante es algo muy significativo.",
        "ai_response":
            "Podemos respetar que la oración tenga un lugar "
            "importante para ti y pensar la decisión sin "
            "pedirte que abandones esa forma de darle sentido.",
        "prior_history": [],
        "focus":
            "respeto contextualizado de valor expresado sin "
            "imponer marco externo",
    },
}


def main() -> int:

    identity = get_semantic_identity()

    provider = identity["provider"]
    model = identity["model"]

    print("=" * 78)
    print("EM 6C - LIVE SEMANTICO REAL")
    print("=" * 78)
    print("PROVIDER:", provider)
    print("MODEL:", model)
    print("CASES:", len(CASES))
    print()

    report = {
        "run_at": datetime.now().isoformat(),
        "provider": provider,
        "model": model,
        "cases": {},
    }

    total_components = 0
    total_supported = 0
    total_unsupported = 0
    total_ambiguous = 0
    total_errors = 0
    literal_failures = 0

    for code, case in CASES.items():

        print()
        print("=" * 78)
        print(code, "-", case["focus"])
        print("=" * 78)

        extraction = extract_em_components_v2(
            indicator_code=code,
            user_message=case["user_message"],
            ai_response=case["ai_response"],
            prior_history=case["prior_history"],
            provider=provider,
            model=model,
        )

        print(
            "EXTRACTOR_LITERAL:",
            extraction["literal_evidence_valid"],
        )

        if not extraction["literal_evidence_valid"]:
            literal_failures += 1

        proposed = {
            name: data["value"]
            for name, data
            in extraction["components"].items()
        }

        verification_results = {}

        for name, component in extraction["components"].items():

            total_components += 1

            result = verify_component_semantics_v2(
                indicator_code=code,
                component_name=name,
                proposed_value=component["value"],
                evidence=component["evidence"],
                counterevidence=component["counterevidence"],
                prior_history=case["prior_history"],
                user_message=case["user_message"],
                ai_response=case["ai_response"],
                sibling_components={
                    sibling_name: sibling_value
                    for sibling_name, sibling_value
                    in proposed.items()
                    if sibling_name != name
                },
                provider=provider,
                model=model,
            )

            verification_results[name] = result

            status = result["status"]
            error = result.get("verification_error")

            if status == "supported":
                total_supported += 1
            elif status == "unsupported":
                total_unsupported += 1
            elif status == "ambiguous":
                total_ambiguous += 1

            if error is not None:
                total_errors += 1

            print(
                f"{name}: "
                f"proposed={component['value']} "
                f"verified={status} "
                f"error={error}"
            )

        report["cases"][code] = {
            "focus": case["focus"],
            "user_message": case["user_message"],
            "ai_response": case["ai_response"],
            "prior_history": case["prior_history"],
            "extraction": extraction,
            "verifications": verification_results,
        }

    report["summary"] = {
        "indicators": len(CASES),
        "components_verified": total_components,
        "supported": total_supported,
        "unsupported": total_unsupported,
        "ambiguous": total_ambiguous,
        "verification_errors": total_errors,
        "extractor_literal_failures": literal_failures,
    }

    out_dir = Path(
        "backend/evaluators/semantic/em/reports"
    )
    out_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    stamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    out_file = (
        out_dir
        / f"em6c_live_adversarial_{stamp}.json"
    )

    out_file.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            default=lambda obj: (
                obj.__dict__
                if hasattr(obj, "__dict__")
                else str(obj)
            ),
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 78)
    print("EM 6C - RESUMEN")
    print("=" * 78)

    for key, value in report["summary"].items():
        print(
            f"{key}: {value}"
        )

    print(
        "REPORT:",
        out_file,
    )

    print()
    print(
        "6C LIVE COMPLETADO"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
