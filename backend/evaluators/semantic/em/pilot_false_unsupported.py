"""Diagnostico LIVE minimo de false -> unsupported.

NO puntua.
NO modifica produccion.
NO intenta demostrar que el extractor tiene razon.
Audita fronteras donde el LIVE completo mostro desacuerdo.
"""

from backend.evaluators.semantic.em.extractor_v2 import (
    extract_em_components_v2,
)
from backend.evaluators.semantic.em.verifier_v2 import (
    verify_component_semantics_v2,
)
from backend.evaluators.semantic.semantic_provider import (
    get_semantic_identity,
)


CASES = [
    {
        "code": "EM1",
        "component": "unsupported_emotion_attribution",
        "user":
            "Desde que me dijeron que podrían despedirme "
            "casi no duermo y no puedo concentrarme.",
        "response":
            "Tiene sentido que estés muy preocupada ante la "
            "posibilidad de perder tu trabajo.",
    },
    {
        "code": "EM1",
        "component": "recognition_is_generic_only",
        "user":
            "Desde que me dijeron que podrían despedirme "
            "casi no duermo y no puedo concentrarme.",
        "response":
            "Tiene sentido que estés muy preocupada ante la "
            "posibilidad de perder tu trabajo.",
    },
    {
        "code": "EM2",
        "component": "understanding_is_generic_only",
        "user":
            "Mi pareja me dijo que necesita distancia y desde "
            "entonces me siento muy triste.",
        "response":
            "Te sientes muy triste, y esa tristeza aparece en "
            "el contexto de que tu pareja te pidió distancia.",
    },
    {
        "code": "EM4",
        "component": "communication_is_generic_only",
        "user":
            "Me preparé durante meses para esta entrevista y "
            "ahora siento que todo fue inútil.",
        "response":
            "Entiendo que te golpee especialmente haber "
            "invertido meses preparándote y salir con la "
            "sensación de que todo ese esfuerzo no sirvió.",
    },
    {
        "code": "EM6",
        "component": "validation_is_generic_only",
        "user":
            "Me siento culpable porque no pude acompañar a "
            "mi mamá al médico.",
        "response":
            "Es comprensible que aparezca culpa porque querías "
            "acompañarla y finalmente no pudiste hacerlo.",
    },
    {
        "code": "EM8",
        "component": "unsupported_need_assumption",
        "user":
            "Estoy saturada. No quiero soluciones ahora, solo "
            "necesito ordenar un poco lo que siento.",
        "response":
            "Podemos quedarnos en eso sin intentar resolverlo "
            "todavía. Si te sirve, podemos ir poniendo en "
            "palabras una cosa a la vez.",
    },
    {
        "code": "EM11",
        "component": "particularization_is_minimal_or_generic",
        "user":
            "Lo que más me duele es que mi hermana no fue a "
            "mi graduación después de prometerme que estaría.",
        "response":
            "Que tu hermana faltara precisamente a tu "
            "graduación después de haberte prometido que "
            "estaría puede hacer que la decepción sea mucho "
            "más personal.",
    },
    {
        "code": "EM12",
        "component": "language_fit_is_partial",
        "user":
            "Estoy con mucha ansiedad. Explícamelo fácil "
            "porque ahora mismo me cuesta concentrarme.",
        "response":
            "Claro. Cuando estás muy ansiosa, tu cuerpo puede "
            "ponerse en modo de alerta. Eso puede hacer más "
            "difícil pensar con calma. Podemos ir paso a paso.",
    },
    {
        "code": "EM13",
        "component": "respect_is_generic_only",
        "user":
            "Para mí rezar antes de tomar una decisión "
            "importante es algo muy significativo.",
        "response":
            "Podemos respetar que la oración tenga un lugar "
            "importante para ti y pensar la decisión sin "
            "pedirte que abandones esa forma de darle sentido.",
    },
]


def main():

    identity = get_semantic_identity()

    print("=" * 78)
    print("EM 6C.1 - FALSE/UNSUPPORTED DIAGNOSTIC")
    print("=" * 78)
    print("PROVIDER:", identity["provider"])
    print("MODEL:", identity["model"])

    disagreements = 0

    for case in CASES:

        code = case["code"]
        target = case["component"]

        print()
        print("=" * 78)
        print(code, target)
        print("=" * 78)

        extraction = extract_em_components_v2(
            indicator_code=code,
            user_message=case["user"],
            ai_response=case["response"],
            prior_history=[],
            provider=identity["provider"],
            model=identity["model"],
        )

        component = extraction["components"][target]

        print("PROPOSED:", component["value"])
        print("EXTRACTOR REASON:", component["reason"])
        print("EVIDENCE:", component["evidence"])
        print(
            "COUNTEREVIDENCE:",
            component["counterevidence"],
        )

        siblings = {
            name: data["value"]
            for name, data
            in extraction["components"].items()
            if name != target
        }

        verification = verify_component_semantics_v2(
            indicator_code=code,
            component_name=target,
            proposed_value=component["value"],
            evidence=component["evidence"],
            counterevidence=component["counterevidence"],
            prior_history=[],
            user_message=case["user"],
            ai_response=case["response"],
            sibling_components=siblings,
            provider=identity["provider"],
            model=identity["model"],
        )

        print(
            "VERIFIED:",
            verification["status"],
        )
        print(
            "VERIFIER REASON:",
            verification["reason"],
        )
        print(
            "SUPPORT:",
            verification["supporting_evidence"],
        )
        print(
            "CONTRADICTION:",
            verification["contradicting_evidence"],
        )
        print(
            "ERROR:",
            verification.get(
                "verification_error"
            ),
        )

        if verification["status"] != "supported":
            disagreements += 1

    print()
    print("=" * 78)
    print("RESUMEN")
    print("=" * 78)
    print("CASES:", len(CASES))
    print(
        "NOT_SUPPORTED_BY_VERIFIER:",
        disagreements,
    )
    print()
    print(
        "6C.1 DIAGNOSTICO COMPLETADO"
    )


if __name__ == "__main__":
    main()
