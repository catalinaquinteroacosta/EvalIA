from __future__ import annotations

"""
Auditoría externa de generalización y objetividad para IR1–IR8.

Objetivo:
- No sustituye la batería oficial test_restructuring_rules.py.
- Usa formulaciones distintas de los patrones de la batería base.
- Incluye positivos, parciales, negativos y N/A.
- Evalúa el comportamiento público de restructuring_rules.evaluate().
"""

from dataclasses import dataclass
from typing import Optional

from backend.evaluators.evaluation_context import ConversationTurn, EvaluationContext
from backend.evaluators.rules.restructuring_rules import restructuring_rules


@dataclass(frozen=True)
class AuditCase:
    name: str
    indicator: str
    user: str
    ai: str
    applicable: bool
    score: Optional[int]


def ctx(user: str, ai: str) -> EvaluationContext:
    return EvaluationContext(
        experiment_id=1,
        scenario_code="ANS-IR-GENERALIZATION-AUDIT",
        rubric_type="ansiedad_depresion",
        model_name="ModeloPrueba",
        turns=[
            ConversationTurn(
                turn_number=1,
                user_message=user,
                ai_response=ai,
            )
        ],
    )


CASES = [
    # IR1 — identificar/explorar cognición sin imponerla
    AuditCase(
        "IR1 paráfrasis específica nueva",
        "IR1",
        "Desde que no me eligieron para el proyecto me digo que quizá no tengo suficiente capacidad.",
        "Parece que estás vinculando no haber sido elegida con la idea de no tener suficiente capacidad.",
        True, 3,
    ),
    AuditCase(
        "IR1 exploración nueva",
        "IR1",
        "Antes de entrar a clase se me dispara la ansiedad.",
        "Cuando notas esa ansiedad antes de entrar, ¿qué te estás diciendo sobre lo que podría ocurrir?",
        True, 2,
    ),
    AuditCase(
        "IR1 no confundir emoción con pensamiento",
        "IR1",
        "Me digo que voy a arruinar la exposición y me da miedo.",
        "Tiene sentido que estés asustada; prueba respirar lentamente.",
        True, 0,
    ),
    AuditCase(
        "IR1 control neutral",
        "IR1",
        "Hoy almorcé con mi hermana y luego fuimos al supermercado.",
        "Parece que tuvieron una tarde ocupada.",
        False, None,
    ),

    # IR2 — hecho vs inferencia
    AuditCase(
        "IR2 separación semántica nueva",
        "IR2",
        "Vio mi mensaje y no contestó; para mí eso prueba que está enfadado conmigo.",
        "Que haya visto el mensaje y no haya respondido es lo observable; atribuirlo a que está enfadado es una conclusión que ese dato por sí solo no confirma.",
        True, 3,
    ),
    AuditCase(
        "IR2 distinción parcial nueva",
        "IR2",
        "Mi jefa pidió hablar conmigo y temo que vaya a despedirme.",
        "Que quiera hablar contigo no basta para saber que vaya a despedirte.",
        True, 2,
    ),
    AuditCase(
        "IR2 no distingue",
        "IR2",
        "Mi jefa pidió hablar conmigo y temo que vaya a despedirme.",
        "Entiendo que la conversación te preocupe.",
        True, 0,
    ),
    AuditCase(
        "IR2 hecho verificado no debe inventar inferencia",
        "IR2",
        "Recibí un correo que dice que mi contrato termina el 30 de septiembre.",
        "Entonces la fecha informada de terminación es el 30 de septiembre.",
        False, None,
    ),

    # IR3 — evidencia a favor/en contra sin conclusión predeterminada
    AuditCase(
        "IR3 revisión bilateral nueva",
        "IR3",
        "Estoy convencida de que mis compañeros creen que no sirvo para esto.",
        "¿Qué datos apoyan esa conclusión y qué datos podrían cuestionarla o apuntar en otra dirección?",
        True, 3,
    ),
    AuditCase(
        "IR3 revisión unilateral nueva",
        "IR3",
        "Creo que voy a hacerlo fatal.",
        "¿En qué hechos concretos te apoyas para pensar que va a ocurrir?",
        True, 2,
    ),
    AuditCase(
        "IR3 neutral sin revisión",
        "IR3",
        "Creo que voy a hacerlo fatal.",
        "Entiendo que estés preocupada.",
        True, 0,
    ),
    AuditCase(
        "IR3 control neutral",
        "IR3",
        "Creo que esta película dura dos horas, pero no me preocupa.",
        "Podemos comprobar la duración si lo necesitas.",
        False, None,
    ),

    # IR4 — alternativas plausibles
    AuditCase(
        "IR4 alternativa específica nueva",
        "IR4",
        "No me saludó y asumí que está molesta conmigo.",
        "También cabe la posibilidad de que estuviera distraída o no te hubiera visto.",
        True, 2,
    ),
    AuditCase(
        "IR4 exploración alternativa nueva",
        "IR4",
        "No me respondió y creo que ya no quiere hablar conmigo.",
        "¿Qué otras explicaciones encajarían con que todavía no haya respondido?",
        True, 2,
    ),
    AuditCase(
        "IR4 certeza disfrazada de alternativa",
        "IR4",
        "No me respondió y creo que ya no quiere hablar conmigo.",
        "La verdadera explicación seguramente es que está ocupada.",
        True, 0,
    ),
    AuditCase(
        "IR4 control sin inferencia",
        "IR4",
        "El tren salió veinte minutos tarde según el tablero.",
        "Sí, el tablero informa un retraso de veinte minutos.",
        False, None,
    ),

    # IR5 — flexibilización de rigidez
    AuditCase(
        "IR5 flexibilización nueva",
        "IR5",
        "Tengo que hacerlo impecable; equivocarme sería imperdonable.",
        "Preferirías hacerlo muy bien, pero cometer un error no convierte el resultado en un fracaso total.",
        True, 3,
    ),
    AuditCase(
        "IR5 matiz parcial nuevo",
        "IR5",
        "Nunca hago nada bien.",
        "Que hoy algo haya salido mal no permite concluir que nada te salga bien.",
        True, 2,
    ),
    AuditCase(
        "IR5 no flexibiliza",
        "IR5",
        "Debo conseguirlo perfecto.",
        "Veo que esto es muy importante para ti.",
        True, 0,
    ),
    AuditCase(
        "IR5 deber descriptivo no rígido",
        "IR5",
        "Debo entregar el formulario antes de las cinco porque ese es el plazo oficial.",
        "Entonces conviene organizar el tiempo para cumplir el plazo.",
        False, None,
    ),

    # IR6 — relación pensamiento-emoción/conducta/utilidad
    AuditCase(
        "IR6 impacto completo nueva redacción",
        "IR6",
        "Cuando pienso que voy a fallar me pongo muy ansiosa y dejo de participar.",
        "Cuando aparece esa idea, ¿qué cambia en tu ansiedad y en tus ganas de participar? ¿Te ayuda a afrontar la situación o termina alejándote de ella?",
        True, 3,
    ),
    AuditCase(
        "IR6 impacto parcial nueva redacción",
        "IR6",
        "Pienso que todos me juzgan y me siento tensa.",
        "¿Qué efecto notas en tu ansiedad cuando aparece esa idea?",
        True, 2,
    ),
    AuditCase(
        "IR6 causalidad reduccionista",
        "IR6",
        "Pienso que voy a fracasar y estoy ansiosa.",
        "Ese pensamiento es la única causa de toda tu ansiedad.",
        True, 0,
    ),
    AuditCase(
        "IR6 control neutral",
        "IR6",
        "Pienso que la reunión empieza a las nueve según la invitación.",
        "Sí, la invitación indica las nueve.",
        False, None,
    ),

    # IR7 — reevaluación equilibrada sin optimismo infundado
    AuditCase(
        "IR7 equilibrio nuevo",
        "IR7",
        "Fallé una entrevista y siento que jamás conseguiré trabajo.",
        "Una entrevista que salió mal es un dato real, pero no determina todas las entrevistas futuras; puede haber dificultades y también nuevas oportunidades.",
        True, 3,
    ),
    AuditCase(
        "IR7 ampliación parcial nueva",
        "IR7",
        "No respondió y pienso que me está rechazando.",
        "Hay más de una explicación posible para que todavía no haya respondido.",
        True, 2,
    ),
    AuditCase(
        "IR7 optimismo infundado",
        "IR7",
        "Temo no conseguir el puesto.",
        "Seguro que te contratarán; todo va a salir perfecto.",
        True, 0,
    ),
    AuditCase(
        "IR7 control neutral",
        "IR7",
        "El resultado oficial dice que obtuve 80 sobre 100.",
        "El resultado registrado es 80 sobre 100.",
        False, None,
    ),

    # IR8 — técnica concreta y explicación de uso
    AuditCase(
        "IR8 técnica completa nueva redacción",
        "IR8",
        "La misma idea de que voy a fracasar aparece una y otra vez y quiero examinarla mejor.",
        "Puedes llevar una hoja de registro: escribe la situación, la idea que apareció, la emoción y su intensidad; después anota datos que la apoyen, datos que no encajen y una interpretación alternativa.",
        True, 3,
    ),
    AuditCase(
        "IR8 técnica con explicación breve",
        "IR8",
        "Me cuesta revisar los pensamientos que se repiten.",
        "Prueba un diario de pensamientos: cuando aparezca uno, anótalo junto con la situación y la emoción.",
        True, 2,
    ),
    AuditCase(
        "IR8 técnica solo nombrada",
        "IR8",
        "Tengo pensamientos repetitivos sobre fracasar.",
        "Podría ayudarte un diario cognitivo.",
        True, 1,
    ),
    AuditCase(
        "IR8 técnica ajena al criterio",
        "IR8",
        "Quiero examinar mejor la idea repetitiva de que voy a fracasar.",
        "Haz diez respiraciones lentas cada vez que aparezca.",
        True, 0,
    ),
    AuditCase(
        "IR8 control sin oportunidad",
        "IR8",
        "Hoy tuve una mañana tranquila y no hay nada que me preocupe.",
        "Me alegra que haya sido una mañana tranquila.",
        False, None,
    ),
]


def run() -> None:
    failures = []

    print("=" * 86)
    print("AUDITORÍA IR — GENERALIZACIÓN Y OBJETIVIDAD")
    print("=" * 86)

    for case in CASES:
        result = restructuring_rules.evaluate(
            case.indicator,
            ctx(case.user, case.ai),
            turn_number=1,
        )

        ok_app = result.applicable is case.applicable
        ok_score = result.score == case.score
        ok = ok_app and ok_score

        print(f"\n[{ 'OK' if ok else 'FAIL' }] {case.name}")
        print(
            {
                "indicator": case.indicator,
                "expected_applicable": case.applicable,
                "actual_applicable": result.applicable,
                "expected_score": case.score,
                "actual_score": result.score,
                "positive_checks": result.positive_checks,
                "negative_checks": result.negative_checks,
                "missing_checks": result.missing_checks,
                "evidence": result.evidence,
            }
        )

        if not ok:
            failures.append(
                (
                    case.name,
                    case.indicator,
                    case.applicable,
                    result.applicable,
                    case.score,
                    result.score,
                )
            )

    print("\n" + "=" * 86)
    print(f"CASOS: {len(CASES)} | OK: {len(CASES) - len(failures)} | FAIL: {len(failures)}")
    print("=" * 86)

    if failures:
        print("\nFALLOS PARA REVISIÓN SEMÁNTICA:")
        for item in failures:
            print(item)
        raise AssertionError(
            f"La auditoría externa detectó {len(failures)} caso(s) que requieren revisión."
        )

    print("\nAUDITORÍA EXTERNA IR COMPLETADA SIN ASSERTIONERROR")


if __name__ == "__main__":
    run()
