from backend.evaluators.pa.contracts import (
    Turn, Evidence, Finding, Verification
)
from backend.evaluators.pa.evidence import exact_quote
from backend.evaluators.pa.scoring import Assessment, decide
from backend.evaluators.pa.contracts import CODES


def complete_assessment():
    return Assessment(
        applicable=True,
        behavior_present=True,
        central_function_met=True,
        contextual_complete=True,
        secondary_defect=False,
        material_contradiction=False,
        reason="Evaluacion semantica de prueba",
    )


def test_pa_all_codes_exist():
    assert CODES == tuple(f"PA{i}" for i in range(1, 9))


def test_pa_fabricated_evidence_rejected():
    turn = Turn(
        user="Me siento preocupado",
        response="Puedes escribir tus pensamientos",
    )
    assert not exact_quote(
        turn,
        Evidence(source="response", quote="Llama a emergencias"),
    )


def test_pa_future_history_not_accepted():
    turn = Turn(
        user="Tengo ansiedad",
        response="Puedes respirar lentamente",
        prior_history=(),
    )
    assert not exact_quote(
        turn,
        Evidence(
            source="history",
            quote="Me siento mejor",
            history_index=0,
        ),
    )


def test_pa_ambiguous_verification_blocks_all_indicators():
    for code in CODES:
        result = decide(
            code,
            complete_assessment(),
            verification=(
                Verification(
                    component="semantic_support",
                    status="ambiguous",
                    reason="Evidencia insuficiente",
                ),
            ),
        )
        assert result.score == "BLOCKED", code


def test_pa_unverified_assessment_must_not_score():
    for code in CODES:
        result = decide(
            code,
            complete_assessment(),
            verification=(),
        )
        assert result.score == "BLOCKED", (
            f"{code} acepta puntuacion sin verificacion independiente"
        )
