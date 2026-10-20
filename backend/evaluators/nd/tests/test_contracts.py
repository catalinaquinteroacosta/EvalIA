from backend.evaluators.nd.contracts import (
    ND_CODES,
    ND_CONDITIONAL,
    ND_GENERAL,
    TurnContext,
    HistoryTurn,
    Evidence,
    NDResult,
)

def test_eight_indicators():
    assert len(ND_CODES) == 8
    assert ND_CONDITIONAL == {"ND1", "ND2", "ND7"}
    assert ND_GENERAL == {
        "ND3", "ND4", "ND5", "ND6", "ND8"
    }

def test_exact_evidence():
    context = TurnContext(
        user="Siento que todo saldra mal",
        response="Entiendo tu preocupacion.",
        prior_history=(
            HistoryTurn("user", "Ayer tuve miedo"),
        ),
    )
    assert Evidence("user", "todo saldra mal").verify_exact(context)
    assert Evidence("history", "Ayer tuve miedo", 0).verify_exact(context)
    assert not Evidence("user", "todo saldrá mal").verify_exact(context)
    assert not Evidence("history", "Ayer tuve miedo", 1).verify_exact(context)

def test_scores_and_blocked():
    NDResult("ND1", "SCORED", 0, "Falla comprobada")
    NDResult("ND1", "NA", None, "Condicion ausente")
    NDResult("ND1", "BLOCKED", None, "Evidencia ambigua")

    try:
        NDResult("ND1", "BLOCKED", 0, "Incorrecto")
    except ValueError:
        pass
    else:
        raise AssertionError("BLOCKED no puede ser cero")

def test_no_future_history():
    context = TurnContext(
        user="Mensaje actual",
        response="Respuesta actual",
        prior_history=(),
    )
    assert not Evidence(
        "history", "Mensaje futuro", 0
    ).verify_exact(context)
