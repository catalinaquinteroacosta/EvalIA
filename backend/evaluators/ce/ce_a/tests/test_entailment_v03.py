from backend.evaluators.ce.ce_a import evidence_verifier as ev


def test_real_ce2_false_positive_v02():
    result = ev.validate_verdict({
        "verdict": "supported",
        "reason": (
            "La evidencia valida la emocion. Aunque la cita "
            "no menciona una reduccion de la exigencia, "
            "no respalda por si sola esa segunda afirmacion. "
            "La interpretacion completa no queda plenamente "
            "cubierta por la evidencia citada."
        ),
    })
    assert result["verdict"] == "ambiguous"
    assert "CONFLICTO INTERNO" in result["reason"]


def test_real_ce1_incomplete_interpretation():
    result = ev.validate_verdict({
        "verdict": "supported",
        "reason": (
            "La cita recomienda descansar, pero la relacion "
            "con los nervios no queda completamente respaldada."
        ),
    })
    assert result["verdict"] == "ambiguous"


def test_complete_support_not_blocked():
    result = ev.validate_verdict({
        "verdict": "supported",
        "reason": (
            "La cita indica expresamente preparar la ropa "
            "y los documentos. Ambas afirmaciones se "
            "encuentran respaldadas."
        ),
    })
    assert result["verdict"] == "supported"


def test_v03_invalidates_old_cache():
    assert ev.VERSION == "ce-a-entailment-0.3.0"
