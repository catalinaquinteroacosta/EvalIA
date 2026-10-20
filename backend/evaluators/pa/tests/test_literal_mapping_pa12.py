
from backend.evaluators.pa.literal_mapping_pa12 import (
    evaluate_mapping,
)


def prop(name, value="present"):
    return {"name": name, "value": value}



def test_pa1_all_components():
    result = evaluate_mapping("PA1", [
        prop("propuesta de acci\u00f3n espec\u00edfica"),
        prop("acci\u00f3n observable"),
        prop("relaci\u00f3n con el problema"),
    ])
    assert result["status"] == "QUESTION_SUPPORTED"


def test_pa1_missing_relation():
    result = evaluate_mapping("PA1", [
        prop("propuesta de acci\u00f3n espec\u00edfica"),
        prop("acci\u00f3n observable"),
        prop("relaci\u00f3n con el problema", "absent"),
    ])
    assert result["status"] == "QUESTION_NOT_FULLY_SUPPORTED"


def test_pa6_alternative_is_sufficient():
    result = evaluate_mapping("PA6", [
        prop("ofrece alternativas"),
        prop("permite adaptar la acci?n", "absent"),
    ])
    assert result["status"] == "QUESTION_SUPPORTED"


def test_pa8_adjustment_is_sufficient():
    result = evaluate_mapping("PA8", [
        prop("forma de revisar resultados", "absent"),
        prop("forma de ajustar el plan"),
    ])
    assert result["status"] == "QUESTION_SUPPORTED"


def test_pa7_inferred_purpose_not_accepted():
    result = evaluate_mapping("PA7", [
        prop("finalidad inferida"),
        prop("coherencia con la necesidad"),
    ])
    assert result["status"] == "BLOCKED"


def test_pa4_unresolved_blocks():
    result = evaluate_mapping(
        "PA4", [], blocked=True
    )
    assert result["status"] == "BLOCKED"


def test_no_scores_assigned():
    result = evaluate_mapping("PA5", [
        prop(
            "Dependencia de comportamientos "
            "realizables por la persona"
        ),
    ])
    assert result["score"] is None
