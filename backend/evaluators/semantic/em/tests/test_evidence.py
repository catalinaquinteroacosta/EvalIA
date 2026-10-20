from backend.evaluators.semantic.em.evidence import (
    SOURCE_AI,
    SOURCE_PREVIOUS,
    SOURCE_USER,
    find_exact_quote,
    validate_component_evidence,
    verify_exact_evidence,
)


PREVIOUS = "Ayer me dijiste que llevabas varios dias preocupada."
USER = "Me siento agotada desde que perdi mi trabajo."
AI = (
    "Tiene sentido que te sientas agotada despues de perder tu trabajo. "
    "¿Que es lo que mas te preocupa ahora?"
)


def test_exact_user_quote_is_valid():
    result = verify_exact_evidence(
        ["Me siento agotada"],
        previous_context=PREVIOUS,
        user_message=USER,
        ai_response=AI,
    )

    assert result.valid is True
    assert result.invalid_quotes == ()
    assert any(
        match.source == SOURCE_USER
        for match in result.matches
    )


def test_exact_ai_quote_is_valid():
    result = verify_exact_evidence(
        ["Tiene sentido que te sientas agotada"],
        previous_context=PREVIOUS,
        user_message=USER,
        ai_response=AI,
    )

    assert result.valid is True
    assert any(
        match.source == SOURCE_AI
        for match in result.matches
    )


def test_exact_previous_context_quote_is_valid():
    result = verify_exact_evidence(
        ["varios dias preocupada"],
        previous_context=PREVIOUS,
        user_message=USER,
        ai_response=AI,
    )

    assert result.valid is True
    assert any(
        match.source == SOURCE_PREVIOUS
        for match in result.matches
    )


def test_paraphrase_is_rejected():
    result = verify_exact_evidence(
        ["Estoy exhausta porque perdi el empleo"],
        previous_context=PREVIOUS,
        user_message=USER,
        ai_response=AI,
    )

    assert result.valid is False
    assert result.invalid_quotes == (
        "Estoy exhausta porque perdi el empleo",
    )


def test_case_change_is_rejected():
    result = verify_exact_evidence(
        ["me siento agotada"],
        previous_context=PREVIOUS,
        user_message=USER,
        ai_response=AI,
    )

    assert result.valid is False


def test_added_whitespace_is_rejected():
    result = verify_exact_evidence(
        [" Me siento agotada "],
        previous_context=PREVIOUS,
        user_message=USER,
        ai_response=AI,
    )

    assert result.valid is False


def test_empty_quote_is_rejected():
    result = verify_exact_evidence(
        [""],
        previous_context=PREVIOUS,
        user_message=USER,
        ai_response=AI,
    )

    assert result.valid is False
    assert result.invalid_quotes == ("",)


def test_one_invalid_quote_invalidates_collection():
    result = verify_exact_evidence(
        [
            "Me siento agotada",
            "frase que nunca existio",
        ],
        previous_context=PREVIOUS,
        user_message=USER,
        ai_response=AI,
    )

    assert result.valid is False
    assert result.invalid_quotes == (
        "frase que nunca existio",
    )


def test_find_exact_quote_preserves_offsets():
    matches = find_exact_quote(
        "agotada",
        user_message=USER,
    )

    assert len(matches) == 1
    match = matches[0]

    assert USER[match.start:match.end] == "agotada"
    assert match.source == SOURCE_USER


def test_component_validates_evidence_and_counterevidence_separately():
    component = {
        "value": "true",
        "evidence": [
            "Tiene sentido que te sientas agotada"
        ],
        "counterevidence": [
            "¿Que es lo que mas te preocupa ahora?"
        ],
        "reason": "Prueba.",
    }

    result = validate_component_evidence(
        component,
        previous_context=PREVIOUS,
        user_message=USER,
        ai_response=AI,
    )

    assert result["evidence_valid"] is True
    assert result["counterevidence_valid"] is True
    assert result["invalid_evidence"] == ()
    assert result["invalid_counterevidence"] == ()


def test_component_does_not_modify_semantic_value():
    component = {
        "value": "unknown",
        "evidence": [],
        "counterevidence": [],
        "reason": "No concluyente.",
    }

    original = dict(component)

    validate_component_evidence(
        component,
        previous_context=PREVIOUS,
        user_message=USER,
        ai_response=AI,
    )

    assert component == original
