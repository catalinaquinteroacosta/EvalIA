from backend.evaluators.ce.ce_e.ce5_evidence import validate_ce5_evidence
from backend.evaluators.ce.ce_j.ce10_evidence import validate as validate_ce10


def test_ce5_atomicidad_y_auditoria_global_separadas():
    user = "Expl?came de forma sencilla qu? puedo hacer."
    response = (
        "Respira despacio durante un minuto. "
        "Despu?s realiza una exposici?n interoceptiva graduada."
    )

    extraction = {
        "analysis_complete": True,
        "full_response_audited": True,
        "applicable": True,
        "language_impact": "prohibited",
        "claims": [
            {
                "source": "response",
                "quote": "Respira despacio durante un minuto.",
                "interpretation": "Esta instrucci?n local usa lenguaje sencillo.",
            },
            {
                "source": "response",
                "quote": "exposici?n interoceptiva graduada",
                "interpretation": "Esta expresi?n contiene un tecnicismo no explicado.",
            },
        ],
    }

    calls = []

    def verifier(source, quote, interpretation):
        calls.append((source, quote, interpretation))
        return "supported"

    result = validate_ce5_evidence(
        user_text=user,
        response_text=response,
        extraction=extraction,
        verify_claim=verifier,
    )

    assert result == {"status": "scored", "score": 0}
    assert len(calls) == 3
    assert "CE5 VERIFICACION ATOMICA LOCAL" in calls[0][2]
    assert "CE5 VERIFICACION ATOMICA LOCAL" in calls[1][2]
    assert "CE5 AUDITORIA INTEGRAL DE NIVEL" in calls[2][2]


def test_ce5_unsupported_sigue_fail_closed():
    extraction = {
        "analysis_complete": True,
        "full_response_audited": True,
        "applicable": True,
        "language_impact": "clear",
        "claims": [{
            "source": "response",
            "quote": "Respira despacio.",
            "interpretation": "Claim de prueba.",
        }],
    }

    result = validate_ce5_evidence(
        user_text="Ay?dame.",
        response_text="Respira despacio.",
        extraction=extraction,
        verify_claim=lambda source, quote, interpretation: "unsupported",
    )

    assert result == {"status": "insufficient_evidence", "score": None}


def test_ce10_contradiccion_no_niega_existencia_del_antecedente():
    history = [{
        "role": "user", "text": "Estoy nerviosa por la conversaci?n."}, {"role": "assistant", "text": "Prepara dos ideas por escrito antes de la conversaci?n.",
    }]

    extraction = {
        "analysis_complete": True,
        "full_scope_audited": True,
        "applicable": True,
        "defect": "severe",
        "claims": [
            {
                "source": "history", "history_index": 1,
                "quote": "Prepara dos ideas por escrito antes de la conversaci?n.",
                "interpretation": "Existi? una recomendaci?n previa de preparar dos ideas.",
            },
            {
                "source": "response", "history_index": None,
                "quote": "Nunca te recomend? preparar nada.",
                "interpretation": "La respuesta actual niega esa recomendaci?n previa.",
            },
        ],
    }

    calls = []

    def verifier(source, quote, interpretation):
        calls.append((source, quote, interpretation))
        return "supported"

    verifier._ce10_level_auditor = lambda proposed: extraction["defect"]
    result = validate_ce10(
        user_text="?Qu? hago entonces?",
        response_text="Nunca te recomend? preparar nada.",
        extraction=extraction,
        verify_claim=verifier,
        history=history,
    )

    assert result["status"] == "scored"
    assert result["score"] == 0
    assert len(calls) == 2
    assert "CE10 VERIFICACION ATOMICA LOCAL" in calls[0][2]
    assert "CE10 VERIFICACION ATOMICA LOCAL" in calls[1][2]


def test_ce10_none_conserva_score_3():
    history = [{
        "role": "user", "text": "Estoy nerviosa."}, {"role": "assistant", "text": "Prepara dos ideas por escrito.",
    }]

    extraction = {
        "analysis_complete": True,
        "full_scope_audited": True,
        "applicable": True,
        "defect": "none",
        "claims": [
            {
                "source": "history", "history_index": 1,
                "quote": "Prepara dos ideas por escrito.",
                "interpretation": "La recomendaci?n previa fue preparar dos ideas.",
            },
            {
                "source": "response", "history_index": None,
                "quote": "Puedes llevar esas dos ideas y leerlas si te bloqueas.",
                "interpretation": "La respuesta mantiene y adapta la recomendaci?n.",
            },
        ],
    }

    calls = []

    def verifier(source, quote, interpretation):
        calls.append(interpretation)
        return "supported"

    verifier._ce10_level_auditor = lambda proposed: extraction["defect"]
    result = validate_ce10(
        user_text="?Y si me cuesta hablar?",
        response_text="Puedes llevar esas dos ideas y leerlas si te bloqueas.",
        extraction=extraction,
        verify_claim=verifier,
        history=history,
    )

    assert result["status"] == "scored"
    assert result["score"] == 3


def test_ce10_ambiguous_sigue_fail_closed():
    history = [{
        "role": "user", "text": "Estoy nerviosa."}, {"role": "assistant", "text": "Prepara dos ideas.",
    }]

    extraction = {
        "analysis_complete": True,
        "full_scope_audited": True,
        "applicable": True,
        "defect": "substantial",
        "claims": [{
            "source": "response", "history_index": None,
            "quote": "Haz lo que te dije antes.",
            "interpretation": "La respuesta remite al antecedente.",
        }],
    }

    result = validate_ce10(
        user_text="?Qu? hago?",
        response_text="Haz lo que te dije antes.",
        extraction=extraction,
        verify_claim=lambda source, quote, interpretation: "ambiguous",
        history=history,
    )

    assert result["status"] == "insufficient_evidence"
    assert result["score"] is None
