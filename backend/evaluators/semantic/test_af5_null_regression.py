import pytest

from backend.evaluators.semantic.af_ai_af5 import (
    AFAI_AF5_Error,
    af5_component_is_confirmed,
    af5_resignation_is_confirmed,
)


@pytest.mark.parametrize("invalid", [None, [], "invalid"])
def test_af5_rejects_invalid_semantic_validation(invalid):
    item = {"semantic_validation": invalid}

    with pytest.raises(AFAI_AF5_Error):
        af5_component_is_confirmed(item, "L")


@pytest.mark.parametrize("invalid", [None, [], "invalid"])
def test_af5_rejects_invalid_component(invalid):
    item = {
        "semantic_validation": {
            "L": invalid,
            "A": {"status": "not_supported"},
            "C": {"status": "not_supported"},
        }
    }

    with pytest.raises(AFAI_AF5_Error):
        af5_component_is_confirmed(item, "L")


def test_af5_accepts_valid_component():
    item = {
        "semantic_validation": {
            "L": {"status": "supported"}
        }
    }

    assert af5_component_is_confirmed(item, "L") is True


def test_af5_resignation_none_is_not_confirmed():
    item = {"semantic_validation": None}

    assert af5_resignation_is_confirmed(item) is False


def test_af5_rejects_null_semantic_validator():
    from backend.evaluators.semantic.af_ai_af5 import (
        _merge_relation_and_validator,
    )

    with pytest.raises(AFAI_AF5_Error):
        _merge_relation_and_validator(
            extractor_status="supported",
            validator=None,
            component="L",
        )


def test_af5_rejects_null_component_before_coherence(monkeypatch):
    from backend.evaluators.semantic import af_ai_af5 as af5

    monkeypatch.setattr(af5, "_validate_l", lambda **kwargs: None)
    monkeypatch.setattr(
        af5, "_validate_a",
        lambda **kwargs: {"status": "not_supported"}
    )
    monkeypatch.setattr(
        af5, "_validate_c",
        lambda **kwargs: {"status": "not_supported"}
    )

    with pytest.raises(AFAI_AF5_Error, match="invalid validation structure for L"):
        af5._validate_acceptance_item(
            item={},
            current_ai="Test response",
            model="test",
            timeout=10,
        )


def test_af5_rejects_null_literal_recovery(monkeypatch):
    from backend.evaluators.semantic import af_ai_af5 as af5

    monkeypatch.setattr(
        af5, "recover_literal_evidence",
        lambda **kwargs: None,
    )

    with pytest.raises(AFAI_AF5_Error):
        af5._validate_l(
            item={
                "limit_description": "Existe una incertidumbre",
                "limit_evidence": {"quote": "Cita inexistente"},
            },
            current_ai="Respuesta sin esa cita literal.",
            model="test",
            timeout=10,
        )


def test_af5_rejects_null_remaining_choice_recovery(monkeypatch):
    from backend.evaluators.semantic import af_ai_af5 as af5

    monkeypatch.setattr(
        af5, "extract_ai_af5_remaining_choice",
        lambda **kwargs: None,
    )

    with pytest.raises(AFAI_AF5_Error):
        af5._recover_remaining_choice(
            item={
                "limit_description": "No puede cambiar el pasado",
                "limit_evidence": {
                    "quote": "No puede cambiar el pasado",
                    "source": "current_ai",
                },
            },
            current_ai="No puede cambiar el pasado.",
            model="test",
            timeout=10,
        )
