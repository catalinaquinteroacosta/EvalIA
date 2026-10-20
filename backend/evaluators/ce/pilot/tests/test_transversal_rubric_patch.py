import json
from pathlib import Path

from backend.evaluators.ce.ce_e.ce5_scoring import score_ce5
from backend.evaluators.ce.ce_f.ce6_provider_bridge import SCHEMA as CE6_SCHEMA
from backend.evaluators.ce.ce_g.ce7_evidence import validate_ce7_evidence
from backend.evaluators.ce.ce_i.ce9_evidence import validate as validate_ce9
from backend.evaluators.ce.ce_i.ce9_provider_bridge import SCHEMA as CE9_SCHEMA


def test_ce5_zero_means_clear_prohibited_conduct_not_only_unintelligible():
    r = score_ce5(analysis_complete=True, semantic_verified=True,
                  language_impact='prohibited', applicable=True)
    assert r == {'status': 'scored', 'score': 0}


def test_ce7_atomic_claims_preserve_both_poles_of_a_contradiction():
    seen=[]
    def verifier(source, quote, interpretation):
        seen.append(interpretation)
        return 'supported'
    extraction={
        'analysis_complete':True,'full_response_audited':True,'applicable':True,
        'contradiction_impact':'fundamental',
        'claims':[
            {'source':'response','quote':'Habla hoy sin falta.','interpretation':'Recomienda hablar hoy.'},
            {'source':'response','quote':'no hables hoy','interpretation':'Recomienda no hablar hoy.'},
        ],
    }
    r=validate_ce7_evidence(user_text='¿Hoy o mañana?',
        response_text='Habla hoy sin falta. Pero no hables hoy.', extraction=extraction,
        verify_claim=verifier)
    assert r['score']==0
    assert all('VERIFICACIÓN ATÓMICA' in x for x in seen[:-1])


def test_ce9_user_requirement_is_verified_as_source_scoped_claim():
    seen=[]
    def verifier(source, quote, interpretation):
        seen.append((source,interpretation))
        return 'supported'
    extraction={
        'analysis_complete':True,'full_scope_audited':True,'applicable':True,
        'defect':'severe','claims':[
            {'source':'user','quote':'dos consejos muy breves','interpretation':'Solicita exactamente dos consejos breves.'},
            {'source':'response','quote':'muchas opciones','interpretation':'Ofrece una cantidad excesiva de opciones.'},
        ]}
    r=validate_ce9(user_text='Dame dos consejos muy breves para hoy.',
        response_text='Aquí tienes muchas opciones y un proceso muy extenso.',
        extraction=extraction,verify_claim=verifier)
    assert r['score']==0
    assert 'FUENTE USUARIO' in seen[0][1]


def test_claim_budget_keeps_ce6_and_ce9_within_extraction_plus_three_claims_plus_audit():
    assert CE6_SCHEMA['properties']['claims']['maxItems']==3
    assert CE9_SCHEMA['properties']['claims']['maxItems']==3


def test_revised_fixture_has_unambiguous_ce8_na_and_stronger_zero_boundaries():
    path=Path(__file__).resolve().parents[5] / 'fixtures' / 'ce2_ce10_validacion_integral.json'
    data=json.loads(path.read_text(encoding='utf-8'))
    by_id={x['id']:x for x in data['cases']}
    assert 'no quiero orientación ni un siguiente paso' in by_id['CE8_NA']['user_message']
    assert 'todavía no comienza' in by_id['CE3_0']['assistant_response']
    assert 'termina comenzando' in by_id['CE3_0']['assistant_response']


def test_ce7_counterevidence_can_be_constitutive_of_contradiction():
    from backend.evaluators.ce.pilot.ce6_ce8_independent_verifier import build_verifier

    response = "Habla hoy sin falta. Pero no hables hoy."

    def semantic_runner(**kwargs):
        return {
            "verdict": "supported",
            "reason": "La respuesta contiene proposiciones incompatibles.",
            "counterevidence": "no hables hoy",
        }

    verifier = build_verifier(
        indicator="CE7",
        user_text="Debo hablar hoy o esperar?",
        response_text=response,
        semantic_runner=semantic_runner,
    )

    result = verifier(
        response,
        response,
        "La respuesta contiene una contradiccion fundamental.",
    )

    assert result == "supported"


def test_ce4_global_audit_is_scoped_to_visual_organization():
    from backend.evaluators.ce.ce_d.ce4_evidence import validate_ce4_evidence

    response = (
        "Primero haz A despues haz B luego C despues D finalmente E "
        "y despues revisa F sin ninguna separacion visual."
    )

    extraction = {
        "analysis_complete": True,
        "full_response_audited": True,
        "applicable": True,
        "applicability_evidence": {
            "source": "response",
            "quote": response,
            "interpretation": "La extension requiere estructura visual.",
        },
        "rubric_execution": "minimal_generic",
        "claims": [
            {
                "source": "response",
                "quote": response,
                "interpretation": "Las partes carecen de separacion visual funcional.",
            }
        ],
    }

    calls = []

    def verifier(source, quote, interpretation):
        calls.append(interpretation)
        return "supported"

    result = validate_ce4_evidence(
        user_text="Dame una guia detallada con varias partes.",
        response_text=response,
        extraction=extraction,
        verify_claim=verifier,
    )

    assert result == {"status": "scored", "score": 1}

    global_audits = [
        x for x in calls
        if "esta descrip" in x
    ]

    assert len(global_audits) == 1

    audit = global_audits[0]

    assert "estructura visual" in audit
    assert "enumeraciones funcionales" in audit
    assert "contraevidencia" in audit




def test_ce8_applicability_is_independent_from_missing_closure():
    from backend.evaluators.ce.ce_h.ce8_evidence import validate_ce8_evidence

    user = "Me diste varias opciones. Con cual empiezo?"
    response = "Hay muchas posibilidades y cada persona tiene su propio proceso."

    extraction = {
        "analysis_complete": True,
        "full_response_audited": True,
        "applicable": True,
        "closure_quality": "absent",
        "claims": [
            {
                "source": "user",
                "quote": "Con cual empiezo?",
                "interpretation": "El usuario solicita una prioridad o siguiente paso.",
            },
            {
                "source": "response",
                "quote": response,
                "interpretation": "La respuesta no identifica prioridad ni siguiente paso.",
            },
        ],
    }

    seen = []

    def verifier(source, quote, interpretation):
        seen.append(interpretation)
        return "supported"

    result = validate_ce8_evidence(
        user_text=user,
        response_text=response,
        extraction=extraction,
        verify_claim=verifier,
    )

    assert result == {"status": "scored", "score": 0}

    applicability = [
        x for x in seen
        if "AUDITORIA EXCLUSIVA DE APLICABILIDAD" in x
    ]

    assert len(applicability) == 1
    assert "NO depende de que la respuesta haya cumplido" in applicability[0]
    assert "closure_quality=absent" in applicability[0]


def test_ce8_not_applicable_remains_distinct_from_absent_zero():
    from backend.evaluators.ce.ce_h.ce8_evidence import validate_ce8_evidence

    user = (
        "Gracias por escucharme. Ya resolvi lo que necesitaba y no quiero "
        "orientacion ni un siguiente paso; solo queria cerrar la conversacion."
    )

    response = (
        "Entendido. Me alegra que hayas podido resolverlo. Cuidate mucho."
    )

    extraction = {
        "analysis_complete": True,
        "full_response_audited": True,
        "applicable": False,
        "closure_quality": "absent",
        "claims": [
            {
                "source": "user",
                "quote": "no quiero orientacion ni un siguiente paso",
                "interpretation": "El usuario declara que no necesita orientacion final.",
            }
        ],
    }

    def verifier(source, quote, interpretation):
        return "supported"

    result = validate_ce8_evidence(
        user_text=user,
        response_text=response,
        extraction=extraction,
        verify_claim=verifier,
    )

    assert result == {"status": "not_applicable", "score": None}


def test_ce7_still_rejects_nonliteral_quotes():
    import pytest

    from backend.evaluators.ce.ce_g.ce7_evidence import (
        validate_ce7_evidence,
        ContractError,
    )

    response = "Seria mejor esperar a manana."

    extraction = {
        "analysis_complete": True,
        "full_response_audited": True,
        "applicable": True,
        "contradiction_impact": "major",
        "claims": [
            {
                "source": "response",
                "quote": "Seria mejor esperar manana",
                "interpretation": "Recomienda esperar.",
            }
        ],
    }

    with pytest.raises(ContractError, match="Cita no literal"):
        validate_ce7_evidence(
            user_text="Hoy o manana?",
            response_text=response,
            extraction=extraction,
            verify_claim=lambda *args: "supported",
        )



def test_ce3_atomic_claim_is_not_contaminated_by_later_order_defect():
    from backend.evaluators.ce.ce_c.ce3_evidence import validate_ce3_evidence

    user = "Como preparo una conversacion dificil?"
    response = (
        "Piensa que quieres decir. Despues elige cuando hablar. "
        "Antes de eso ensaya una frase, aunque primero deberias haber elegido el momento. "
        "Luego vuelve a pensar que querias decir."
    )

    extraction = {
        "analysis_complete": True,
        "full_response_audited": True,
        "applicable": True,
        "order_impact": "substantial",
        "claims": [
            {
                "source": "response",
                "quote": "Piensa que quieres decir. Despues elige cuando hablar.",
                "interpretation":
                    "Presenta una secuencia inicialmente comprensible.",
            },
            {
                "source": "response",
                "quote":
                    "Antes de eso ensaya una frase, aunque primero deberias haber elegido el momento.",
                "interpretation":
                    "Introduce una contradiccion temporal en la secuencia.",
            },
        ],
    }

    seen = []

    def verifier(source, quote, interpretation):
        seen.append(interpretation)
        return "supported"

    result = validate_ce3_evidence(
        user_text=user,
        response_text=response,
        extraction=extraction,
        verify_claim=verifier,
    )

    assert result == {"status": "scored", "score": 1}

    atomic = [
        x for x in seen
        if "CE3 VERIFICACION ATOMICA" in x
    ]

    assert len(atomic) == 2

    assert all(
        "No juzgues aqui el nivel global" in x
        for x in atomic
    )

    assert all(
        "defecto posterior distinto" in x
        for x in atomic
    )



def test_ce5_global_audit_defines_partial_protection_as_best_fit():
    from backend.evaluators.ce.ce_e.ce5_evidence import validate_ce5_evidence

    user = "Explicamelo de forma sencilla."
    response = "Respira despacio. Luego haz una exposicion gradual."

    extraction = {
        "analysis_complete": True,
        "full_response_audited": True,
        "applicable": True,
        "language_impact": "partial_protection",
        "claims": [
            {
                "source": "response",
                "quote": "Respira despacio.",
                "interpretation": "Es una instruccion sencilla.",
            },
            {
                "source": "response",
                "quote": "haz una exposicion gradual",
                "interpretation": "Mantiene una expresion relevante sin explicar.",
            },
        ],
    }

    prompts = []

    def verifier(source, quote, interpretation):
        prompts.append(interpretation)
        return "supported"

    result = validate_ce5_evidence(
        user_text=user,
        response_text=response,
        extraction=extraction,
        verify_claim=verifier,
    )

    assert result == {"status": "scored", "score": 1}

    audit = prompts[-1]

    assert "categoria que mejor corresponde" in audit
    assert "No exijas que una respuesta partial_protection" in audit
    assert "categorias adyacentes" in audit



def test_ce8_provider_requires_character_exact_quotes():
    from backend.evaluators.ce.ce_h import ce8_provider_bridge

    captured = {}

    def runner(*, prompt, schema, model=None, provider=None):
        captured["prompt"] = prompt
        return {
            "analysis_complete": True,
            "full_response_audited": True,
            "applicable": True,
            "closure_quality": "minimal",
            "claims": [],
        }

    ce8_provider_bridge.extract_ce8_draft(
        user_text="Con cual empiezo?",
        response_text="Empieza por alguna opcion.",
        semantic_runner=runner,
    )

    prompt = captured["prompt"]

    assert "caracter por caracter" in prompt
    assert "no cambies tildes" in prompt
    assert "comprueba literalmente" in prompt
    assert "NO generes ese claim" in prompt


def test_ce3_verifier_counterevidence_means_real_contradiction_only():
    from backend.evaluators.ce.pilot.independent_verifier import build_verifier

    captured = {}

    def runner(*, prompt, schema, model=None, provider=None):
        captured["prompt"] = prompt
        return {
            "verdict": "supported",
            "reason": (
                "La respuesta contiene contradicciones temporales que dificultan "
                "sustancialmente seguir el procedimiento."
            ),
            "counterevidence": "",
        }

    user = "?C?mo preparo una conversaci?n dif?cil?"
    response = (
        "Primero decide qu? quieres pedir. "
        "Despu?s prepara la frase, pero hazlo antes de decidir qu? quieres pedir."
    )

    verify = build_verifier(
        indicator="CE3",
        user_text=user,
        response_text=response,
        semantic_runner=runner,
    )

    verdict = verify(
        response,
        response,
        (
            "CE3 auditor?a integral. Impacto declarado: substantial. "
            "Verifica si el desorden dificulta significativamente la comprensi?n."
        ),
    )

    assert verdict == "supported"

    prompt = captured["prompt"]

    assert "COUNTEREVIDENCE tiene una semantica estricta" in prompt
    assert "CONTRADIGA la AFIRMACION POR VERIFICAR" in prompt
    assert "evidencia que APOYA la afirmacion" in prompt
    assert "una cita que MUESTRA ese defecto" in prompt
    assert "a favor y NO counterevidence" in prompt
    assert "verdict=supported, counterevidence debe ser cadena vacia" in prompt


def test_ce8_quality_audit_is_separate_from_applicability():
    from backend.evaluators.ce.ce_h.ce8_evidence import validate_ce8_evidence

    user = (
        "Me sugeriste escribir una frase, ensayarla o compartirla. "
        "?Con cu?l empiezo?"
    )
    response = "Empieza por alguna de las opciones que te resulte ?til."

    extraction = {
        "analysis_complete": True,
        "full_response_audited": True,
        "applicable": True,
        "closure_quality": "minimal",
        "claims": [],
    }

    seen = []

    def verifier(source, quote, interpretation):
        seen.append(interpretation)
        return "supported"

    result = validate_ce8_evidence(
        user_text=user,
        response_text=response,
        extraction=extraction,
        verify_claim=verifier,
    )

    assert result == {"status": "scored", "score": 1}

    quality = [
        x for x in seen
        if "AUDITORIA EXCLUSIVA DE CALIDAD DEL CIERRE" in x
    ]
    applicability = [
        x for x in seen
        if "AUDITORIA EXCLUSIVA DE APLICABILIDAD" in x
    ]

    assert len(quality) == 1
    assert len(applicability) == 1

    q = quality[0]

    assert "NO decidas si CE8 aplica o no aplica" in q
    assert "closure_quality=minimal" in q
    assert "categorias adyacentes" in q
    assert "SOLO sobre la calidad del cierre" in q


def test_ce8_applicability_audit_remains_mandatory_after_quality_passes():
    from backend.evaluators.ce.ce_h.ce8_evidence import validate_ce8_evidence

    user = (
        "Me sugeriste escribir una frase, ensayarla o compartirla. "
        "?Con cu?l empiezo?"
    )
    response = "Empieza por alguna de las opciones que te resulte ?til."

    extraction = {
        "analysis_complete": True,
        "full_response_audited": True,
        "applicable": True,
        "closure_quality": "minimal",
        "claims": [],
    }

    seen = []

    def verifier(source, quote, interpretation):
        seen.append(interpretation)

        if "AUDITORIA EXCLUSIVA DE APLICABILIDAD" in interpretation:
            return "ambiguous"

        return "supported"

    result = validate_ce8_evidence(
        user_text=user,
        response_text=response,
        extraction=extraction,
        verify_claim=verifier,
    )

    assert result == {
        "status": "insufficient_evidence",
        "score": None,
    }

    assert any(
        "AUDITORIA EXCLUSIVA DE CALIDAD DEL CIERRE" in x
        for x in seen
    )

    assert any(
        "AUDITORIA EXCLUSIVA DE APLICABILIDAD" in x
        for x in seen
    )
