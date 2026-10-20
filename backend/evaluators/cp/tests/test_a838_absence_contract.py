from pathlib import Path


def test_absence_requires_independent_audit():
    source = Path(
        "backend/evaluators/cp/verifier.py"
    ).read_text(encoding="utf-8")

    assert (
        "Primero verifica independientemente"
        in source
    )
    assert (
        "unsupported exige una contradiccion real"
        in source
    )
    assert (
        "ambiguous corresponde a incertidumbre real"
        in source
    )


def test_no_forced_false_support():
    source = Path(
        "backend/evaluators/cp/verifier.py"
    ).read_text(encoding="utf-8")

    assert (
        "No conviertas automaticamente valores false"
        in source
    )
