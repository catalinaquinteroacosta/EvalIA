
import ast
from pathlib import Path

SOURCE = Path(
    "backend/evaluators/pa/semantic_pilot.py"
).read_text(encoding="utf-8-sig")

def test_valid_python():
    ast.parse(SOURCE)

def test_pa4_contract():
    assert "PA4: distingue recurso sugerido" in SOURCE

def test_pa6_contract():
    assert "PA6: una lista de recomendaciones" in SOURCE

def test_pa8_contract():
    assert "PA8: revisar preocupaciones" in SOURCE

def test_independent_verifier_contract():
    assert "CONTRATO SEMANTICO PA ? VERIFICACION INDEPENDIENTE" in SOURCE
