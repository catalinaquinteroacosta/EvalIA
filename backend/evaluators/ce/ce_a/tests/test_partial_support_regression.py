from backend.evaluators.ce.ce_a import evidence_verifier as ev


def test_real_false_positive_is_blocked():
    result = ev.validate_verdict({
        "verdict": "supported",
        "reason": (
            "La evidencia respalda solo una parte "
            "de la interpretaci?n, no ambas."
        ),
    })
    assert result["verdict"] == "ambiguous"


def test_original_real_reason_is_blocked():
    result = ev.validate_verdict({
        "verdict": "supported",
        "reason": (
            "La evidencia valida expl?citamente la emoci?n, "
            "pero la reducci?n de la exigencia no est? "
            "contenida en la evidencia citada. "
            "Solo respalda una parte, no ambas."
        ),
    })
    assert result["verdict"] == "ambiguous"


def test_fully_supported_remains_supported():
    result = ev.validate_verdict({
        "verdict": "supported",
        "reason": (
            "La cita expresa preparar ropa y documentos. "
            "Todas las afirmaciones est?n respaldadas."
        ),
    })
    assert result["verdict"] == "supported"


def test_explicit_rejection_remains_rejected():
    result = ev.validate_verdict({
        "verdict": "not_supported",
        "reason": "La segunda afirmaci?n no est? respaldada.",
    })
    assert result["verdict"] == "not_supported"


def test_new_verifier_version():
    assert ev.VERSION == "ce-a-entailment-0.3.0"
