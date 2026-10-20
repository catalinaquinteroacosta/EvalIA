import pytest

from backend.evaluators.ce.ce_a.ce1_need_inventory import (
    build_ce1_need_inventory,
)


def extraction():
    return {
        "explicit_needs": [
            {
                "interpretation": "Preparar documentos.",
                "user_evidence": "preparar documentos",
            },
            {
                "interpretation": "Practicar respuestas.",
                "user_evidence": "practicar respuestas",
            },
        ],
        "contextual_needs": [
            {
                "interpretation": "Preparar la entrevista.",
                "source": "prior_context",
                "evidence": "entrevista",
                "justification": "Solicitud anterior.",
            },
            {
                "interpretation": "Orientacion contextual.",
                "source": "implicit",
                "evidence": "me preocupa",
                "justification": "Necesidad inferida.",
            },
        ],
    }


def test_all_needs_are_preserved():
    result = build_ce1_need_inventory(extraction())
    assert len(result) == 4
    assert [
        (r["origin_field"], r["origin_index"])
        for r in result
    ] == [
        ("explicit_needs", 0),
        ("explicit_needs", 1),
        ("contextual_needs", 0),
        ("contextual_needs", 1),
    ]


def test_implicit_need_remains_pending():
    result = build_ce1_need_inventory(extraction())
    assert result[-1]["status"] == "pending_implicit_contract"


def test_no_automatic_semantic_authorization():
    result = build_ce1_need_inventory(extraction())
    assert all(
        r["status"].startswith("pending")
        for r in result
    )


def test_missing_fields_fail():
    with pytest.raises(ValueError):
        build_ce1_need_inventory({"explicit_needs": []})


def test_invalid_source_fails():
    data = extraction()
    data["contextual_needs"][0]["source"] = "unknown"
    with pytest.raises(ValueError):
        build_ce1_need_inventory(data)
