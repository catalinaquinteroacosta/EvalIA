"""Fronteras CE1: verifica el puntuador con componentes YA verificados.
NO simula ni acredita la capacidad de extracción de OpenAI.
"""
import pytest
from backend.evaluators.ce.ce_a.ce1_scoring import score_ce1, CE1ScoringError

@pytest.mark.parametrize("case,coverage,impacts,expected", [
    ("P1_respuesta_breve", "addressed", [], 3),
    ("P2_digresion_secundaria", "addressed", ["minor"], 2),
    ("P3_digresion_dominante", "partially_addressed", ["major"], 1),
    ("P5_complemento_util", "addressed", [], 3),
    ("P6B_oferta_opcional", "addressed", [], 3),
])
def test_fronteras_componentes_verificados(case, coverage, impacts, expected):
    issues = [{"description": "Incidencia contextual verificada", "impact": impact, "evidence_verified": True} for impact in impacts]
    result = score_ce1(primary_coverage=coverage, issues=issues, analysis_complete=True)
    assert result["status"] == "scored", case
    assert result["score"] == expected, case

def test_p4_desvio_total_requiere_verificacion_independiente():
    result = score_ce1(primary_coverage="unaddressed", issues=[], analysis_complete=True)
    assert result["status"] == "requires_total_deviation_check"
    assert result["score"] is None

def test_p6_tecnicas_no_solicitadas_no_se_puntuan_por_defecto():
    # P6=2 es hipótesis de adjudicación; CE1 debe verificar primero
    # que hay una digresión REAL, no confundir sobrecarga CE2/CE9.
    result = score_ce1(primary_coverage="addressed", issues=[], analysis_complete=False)
    assert result["status"] == "insufficient_evidence"
    assert result["score"] is None

def test_incidencia_sin_evidencia_verificada_no_puntua():
    with pytest.raises(CE1ScoringError):
        score_ce1(primary_coverage="addressed", issues=[{
            "description": "Digresion", "impact": "minor", "evidence_verified": False
        }], analysis_complete=True)
