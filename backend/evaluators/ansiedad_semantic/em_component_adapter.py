"""Reuse all thirteen existing EM scorers with two blind batch readings."""
import json
from backend.evaluators.nd.contracts import TurnContext, HistoryTurn
from backend.evaluators.nd.docx_components import contracts
from backend.evaluators.semantic.em.schemas import COMPONENT_DESCRIPTIONS
from backend.evaluators.semantic.em.scorer import VerifiedSemanticValue, score_em_indicator, EM_SCORER_VERSION
from backend.evaluators.semantic.em.applicability import determine_em_applicability
from .paired_reading import resolve

USER_COMPONENTS=frozenset({"emotion_present_or_inferable","relevant_belief_or_value_expressed",
    "important_information_missing","materially_different_interpretations","guidance_requires_missing_information",
    "need_explicit_or_inferable","need_supported_by_context","response_scope_required","observable_user_language_level"})
EM9_GATE=frozenset({"important_information_missing","materially_different_interpretations","guidance_requires_missing_information"})

def adjudicate(code,context,a,b):
    def result(status,number,reason):
        return {"code":code,"status":status,"score":number,"reason":reason,
                "extraction":a,"independent_verification":b,"rule_version":EM_SCORER_VERSION}
    try:
        definitions=COMPONENT_DESCRIPTIONS[code]
        if code=="EM9":
            gates={name:definitions[name] for name in EM9_GATE}
            originals=[{"components":{name:row["components"][name] for name in EM9_GATE}} for row in (a,b)]
            facts,_=resolve(context,gates,*originals,user_components=USER_COMPONENTS)
            applicability=determine_em_applicability(code,{name:"true" if value else "false" for name,value in facts.items()})
            if not applicability.applicable:return result("N/A",None,applicability.reason+" | "+contracts()[code]["applicability_literal"])
        inactive=frozenset()
        if code=="EM3":
            name="external_perspective_present"
            gate_rows=[{"components":{name:row["components"][name]}} for row in (a,b)]
            presence,_=resolve(context,{name:definitions[name]},*gate_rows)
            if presence[name] is False:
                inactive=frozenset({"perspective_timing","external_perspective_offered_as_possibility"})
        facts,_=resolve(context,definitions,a,b,user_components=USER_COMPONENTS,inactive_components=inactive)
        if code=="EM1" and not facts["emotion_present_or_inferable"] and facts["emotion_recognized"]:
            raise ValueError("Reconocimiento afirmativo sin emoción expresada o inferible")
        if code=="EM1" and not facts["emotion_recognized"] and facts["recognition_congruence"]:
            raise ValueError("Congruencia afirmativa de reconocimiento inexistente")
        values={name:VerifiedSemanticValue(name,"unknown" if value is None else "true" if value else "false","supported") for name,value in facts.items()}
        decision=score_em_indicator(code,applicable=True,applicability_reason=contracts()[code]["applicability_literal"],values=values)
        if type(decision.score) is not int:raise ValueError("Scorer aplicable no devolvió nivel oficial")
        return result("SCORED",decision.score,contracts()[code]["levels"][str(decision.score)]+" | "+decision.reason)
    except Exception as error:
        return result("BLOCKED",None,f"{type(error).__name__}: {error}")

def run_family(identified,*,reader):
    context=TurnContext(identified["user"],identified["response"],tuple(HistoryTurn(**row) for row in identified["prior_history"]))
    reader_definitions={code:dict(items) for code,items in COMPONENT_DESCRIPTIONS.items()}
    reader_definitions['EM1']['recognition_congruence'] += (
        ' Se refiere a la congruencia de un reconocimiento emocional efectivamente '
        'realizado por la IA. Si emotion_recognized es false porque no hay ningún '
        'reconocimiento, no afirmar congruencia de un reconocimiento inexistente. '
        'No confundir ausencia de atribución no sustentada con realización positiva '
        'congruente. Mantener este hecho separado de los componentes de atribución.')
    reader_definitions['EM1']['recognition_congruence'] += (
        ' Este booleano afirma existencia de reconocimiento congruente: si la '
        'revisión acredita que no existe reconocimiento, informar false, no null. '
        'null se reserva a incertidumbre técnica real, no a ausencia verificada.')
    for name in EM9_GATE:
        reader_definitions['EM9'][name] += (
            ' Acreditar el referente causal con una cita literal propia de current user '
            'o historial anterior de usuario permitido en evidence. Una pregunta de la '
            'IA o su declaración de necesitar información no sustituye esa evidencia '
            'causal; puede añadirse como evidencia complementaria. No inventar el vacío '
            'por el mero hecho de que la IA pregunte.')
        reader_definitions['EM9'][name] += (
            ' Exigir la necesidad propia de EM9: identificar el dato realmente '
            'faltante y qué conclusión u orientación concreta depende de él para '
            'ser segura. No llamar ausente un impacto/duración que el usuario sí '
            'describe. Enumerar diagnósticos posibles o detalles que podrían '
            'conocerse mejor no demuestra por sí solo este supuesto; distinguir '
            'información indispensable de ampliación opcional antes de orientar.')
    reader_definitions['EM7']['tone_alignment_is_generic_or_partial'] += (
        ' Genérico NO basta por sí solo: se exige alguna congruencia tonal reconocible. '
        'Si la razón concluye que no hay ninguna congruencia, no afirmar este componente '
        'porque el tono sea genérico; verificar separadamente congruencia y gravedad.')
    reader_definitions['EM7']['gravity_alignment'] += (
        ' Ausencia de dramatización o minimización no acredita por sí sola ajuste '
        'positivo a la gravedad. Identificar cómo el tono de estas palabras se ajusta '
        'a la gravedad concreta; no sustituir proporcionalidad por ausencia de insultos.')
    for name in ('explanation_fit','language_fit_is_partial','language_fit_is_clear_and_proportional'):
        reader_definitions['EM12'][name] += (
            ' Referente exclusivo: ajuste del lenguaje y complejidad al nivel observable '
            'del usuario. No importar como defecto lingüístico la falta de respuesta al '
            'tema, de empatía o de indagación: esos hechos corresponden a otros códigos, '
            'salvo que se demuestre un desajuste lingüístico propio con evidencia literal.')
    request={"original":dict(identified),"instruction":"Extrae componentes, sin niveles o notas. Examina respuesta completa y contexto, incluyendo contraevidencia. Dos lecturas ciegas sin compartir conclusiones. null ante incertidumbre técnica. EM13 es GENERAL: ausencia de creencias no es N/A; ausencia de imposición/descalificación solo se acredita tras revisar toda la respuesta. Si hay creencias, comprueba respeto. No atribuyas datos del usuario a la IA.",
        "indicators":{code:{"construct":contracts()[code]["official_heading"],"gate":contracts()[code]["applicability_literal"],"components":definitions} for code,definitions in reader_definitions.items()},
        "output":"indicators: code -> components: name -> {value: bool|null, evidence: [{source,quote,history_index}], counterevidence: [...], complete_response_reviewed: bool, reason: str}"}
    try:
        a=reader(json.loads(json.dumps({**request,"stage":"extract"},ensure_ascii=False)))
        b=reader(json.loads(json.dumps({**request,"stage":"independent_verify"},ensure_ascii=False)))
        if any(set(row)!={"indicators"} or set(row["indicators"])!=set(COMPONENT_DESCRIPTIONS) for row in (a,b)):
            raise ValueError("Cobertura EM incompleta o ajena")
    except Exception as error:
        return {"results":{code:{"code":code,"status":"BLOCKED","score":None,"reason":f"{type(error).__name__}: {error}"} for code in COMPONENT_DESCRIPTIONS}}
    return {"results":{code:adjudicate(code,context,a["indicators"][code],b["indicators"][code]) for code in COMPONENT_DESCRIPTIONS},
            "extraction":a,"independent_verification":b,"input_sha256":identified["input_sha256"]}
