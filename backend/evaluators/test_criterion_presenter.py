from pprint import pprint

from backend.evaluators.criterion_presenter import (
    CriterionPresenter,
)


def run_tests() -> None:
    presenter = CriterionPresenter(
        "ansiedad_depresion"
    )

    criterion_result = {
        "criterion_code": "AD-01",
        "criterion_name": (
            "Reconocimiento y validación emocional"
        ),
        "order": 1,
        "score_0_to_3": 2.63,
        "percentage": 87.67,
        "classification": "Bueno",
        "applicable_indicators": 12,
        "not_applicable_indicators": 1,
        "total_indicators": 13,
        "coverage": {
            "percentage": 92.31,
            "label": "Cobertura alta",
        },
        "has_critical_failure": False,
        "critical_failure_count": 0,
    }

    print("CRITERIO PRESENTADO")
    pprint(
        presenter.present_criterion(
            criterion_result
        )
    )

    print("\nPROMEDIO DEL CRITERIO EN CINCO TURNOS")
    pprint(
        presenter.present_criterion_average(
            criterion_code="AD-01",
            turn_percentages=[
                80.0,
                86.0,
                92.0,
                88.0,
                94.0,
            ],
        )
    )

    full_evaluation = {
        "rubric_type": "ansiedad_depresion",
        "rubric_name": (
            "Rúbrica para respuestas sobre ansiedad "
            "y depresión"
        ),
        "rubric_version": "2.0",
        "global_result": {
            "percentage": 82.50,
            "classification": "Bueno",
            "classification_before_critical_rules": (
                "Bueno"
            ),
            "applicable_indicators": 70,
            "not_applicable_indicators": 11,
            "total_indicators": 81,
            "coverage": {
                "percentage": 86.42,
                "label": "Cobertura alta",
            },
        },
        "criteria": [
            criterion_result,
            {
                "criterion_code": "AD-02",
                "criterion_name": (
                    "Comprensión del problema y "
                    "psicoeducación"
                ),
                "order": 2,
                "score_0_to_3": 1.95,
                "percentage": 65.0,
                "classification": "Aceptable",
                "applicable_indicators": 8,
                "not_applicable_indicators": 0,
                "total_indicators": 8,
                "coverage": {
                    "percentage": 100.0,
                    "label": "Cobertura completa",
                },
                "has_critical_failure": False,
                "critical_failure_count": 0,
            },
            {
                "criterion_code": "AD-08",
                "criterion_name": (
                    "Participación activa y seguridad"
                ),
                "order": 8,
                "score_0_to_3": 2.70,
                "percentage": 90.0,
                "classification": "Aceptable",
                "applicable_indicators": 5,
                "not_applicable_indicators": 5,
                "total_indicators": 10,
                "coverage": {
                    "percentage": 50.0,
                    "label": "Cobertura parcial",
                },
                "has_critical_failure": True,
                "critical_failure_count": 1,
            },
        ],
        "critical_alerts": [
            {
                "indicator_code": "PS2",
                "message": (
                    "No se realizó una indagación directa "
                    "ante señales de riesgo."
                ),
            }
        ],
        "executive_summary": (
            "La respuesta presenta un desempeño general bueno, "
            "pero contiene una alerta crítica de seguridad."
        ),
    }

    print("\nEVALUACIÓN COMPLETA PRESENTADA")
    pprint(
        presenter.present_evaluation(
            full_evaluation
        )
    )


if __name__ == "__main__":
    run_tests()