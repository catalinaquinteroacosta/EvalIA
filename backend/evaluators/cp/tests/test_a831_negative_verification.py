from pathlib import Path

from backend.evaluators.cp.verifier import (
    build_cp_verifier_prompt,
)


def test_a831_negative_evidence_contract():
    source = Path(
        "backend/evaluators/cp/verifier.py"
    ).read_text(encoding="utf-8")

    assert (
        "No exijas una cita positiva de un defecto inexistente."
        in source
    )

    assert (
        "No traslades defectos de otros indicadores."
        in source
    )

    assert (
        "cada valor requiere auditoria independiente"
        in source
    )


def test_a831_preserves_fail_closed_instructions():
    source = Path(
        "backend/evaluators/cp/verifier.py"
    ).read_text(encoding="utf-8")

    assert "marca unsupported" in source
    assert "marca ambiguous" in source
    assert "marca supported" in source
