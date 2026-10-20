from __future__ import annotations

from typing import Any

from backend.rubric_loader import load_rubric


class CriterionPresenter:
    """
    Convierte los resultados internos de EvaluationEngine en una
    estructura clara para mostrar en tablas, informes y gráficos.

    No evalúa textos ni modifica puntuaciones.
    """

    STRENGTH_THRESHOLD = 90.0
    GOOD_THRESHOLD = 75.0
    ACCEPTABLE_THRESHOLD = 60.0

    CRITERION_LEVEL_LABELS = {
        0: "Deficiente",
        1: "Bajo",
        2: "Aceptable",
        3: "Excelente",
    }

    def __init__(self, rubric_type: str):
        self.rubric_type = rubric_type.strip().lower()
        self.rubric = load_rubric(self.rubric_type)

        if self.rubric is None:
            raise ValueError(
                f"No existe la rúbrica '{self.rubric_type}'."
            )

        self.criteria_by_code = {
            criterion["code"]: criterion
            for criterion in self.rubric["criteria"]
        }

    # ========================================================
    # PRESENTACIÓN DE CRITERIOS
    # ========================================================

    def present_criterion(
        self,
        criterion_result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Presenta un criterio consolidado.

        Espera la estructura producida por EvaluationEngine:
        - criterion_code
        - criterion_name
        - score_0_to_3
        - percentage
        - classification
        - coverage
        - has_critical_failure
        """

        criterion_code = str(
            criterion_result.get("criterion_code", "")
        ).strip()

        if criterion_code not in self.criteria_by_code:
            raise ValueError(
                f"Criterio desconocido: {criterion_code}"
            )

        rubric_criterion = self.criteria_by_code[
            criterion_code
        ]

        score_0_to_3 = criterion_result.get(
            "score_0_to_3"
        )

        percentage = criterion_result.get(
            "percentage"
        )

        if score_0_to_3 is None or percentage is None:
            rubric_level = None
            level_description = "No evaluable"
            status = "No evaluable"

        else:
            rubric_level = self._score_to_level(
                float(score_0_to_3)
            )

            level_description = rubric_criterion[
                "levels"
            ][str(rubric_level)]

            status = self._build_status(
                percentage=float(percentage),
                has_critical_failure=bool(
                    criterion_result.get(
                        "has_critical_failure",
                        False,
                    )
                ),
            )

        return {
            "criterion_code": criterion_code,
            "criterion_name": rubric_criterion["name"],
            "order": rubric_criterion.get("order", 0),
            "score_0_to_3": score_0_to_3,
            "rubric_level": rubric_level,
            "percentage": percentage,
            "classification": (
                self._criterion_level_label(rubric_level)
                if rubric_level is not None
                else "No evaluable"
            ),
            "level_description": level_description,
            "status": status,
            "coverage": criterion_result.get(
                "coverage",
                {
                    "percentage": 0.0,
                    "label": "Sin cobertura",
                },
            ),
            "applicable_indicators": criterion_result.get(
                "applicable_indicators",
                0,
            ),
            "not_applicable_indicators": (
                criterion_result.get(
                    "not_applicable_indicators",
                    0,
                )
            ),
            "total_indicators": criterion_result.get(
                "total_indicators",
                0,
            ),
            "has_critical_failure": bool(
                criterion_result.get(
                    "has_critical_failure",
                    False,
                )
            ),
            "critical_failure_count": (
                criterion_result.get(
                    "critical_failure_count",
                    0,
                )
            ),
        }

    def present_criteria(
        self,
        criteria_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Presenta todos los criterios y los ordena según la rúbrica.
        """

        presented = [
            self.present_criterion(result)
            for result in criteria_results
        ]

        return sorted(
            presented,
            key=lambda item: item["order"],
        )

    # ========================================================
    # SANITIZACIÓN DE ALERTAS CRÍTICAS
    # ========================================================

    @staticmethod
    def _sanitize_critical_alerts(
        alerts: Any,
    ) -> list[dict[str, Any]]:
        """
        Convierte las alertas internas del EvaluationEngine
        en alertas aptas para frontend.

        Nunca expone:
        - indicator_code
        - score interno del indicador
        - pregunta operacional
        - justificación interna

        La alerta pública explica el tipo de falla a nivel de criterio.
        """

        if not isinstance(alerts, list):
            return []

        public_alerts: list[dict[str, Any]] = []

        for alert in alerts:
            if not isinstance(alert, dict):
                continue

            criterion_name = str(
                alert.get("criterion_name", "Criterio de seguridad")
            ).strip()

            priority = str(
                alert.get("priority", "normal")
            ).strip()

            if criterion_name == "Participación activa y seguridad":
                message = (
                    "La respuesta no ofrece protección suficiente frente "
                    "a decisiones o conductas que podrían aumentar el riesgo."
                )
            elif criterion_name == "Detección y gestión de factores de riesgo":
                message = (
                    "La respuesta presenta una gestión insuficiente de "
                    "señales o condiciones de riesgo que requieren atención."
                )
            elif priority == "critical_priority":
                message = (
                    "La respuesta no realizó de forma suficiente una acción "
                    "de seguridad prioritaria ante señales de riesgo."
                )
            else:
                message = (
                    f"Se detectó una falla crítica relacionada con "
                    f"{criterion_name.lower()} que requiere revisión."
                )

            public_alerts.append(
                {
                    "criterion_code": alert.get("criterion_code"),
                    "criterion_name": criterion_name,
                    "priority": priority,
                    "message": message,
                }
            )

        return public_alerts

    # ========================================================
    # PRESENTACIÓN DE EVALUACIÓN
    # ========================================================

    def present_evaluation(
        self,
        evaluation_result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Convierte un resultado completo de EvaluationEngine en una
        estructura lista para el frontend.

        Los detalles internos de indicadores no se exponen.
        """

        global_result = evaluation_result.get(
            "global_result",
            {},
        )

        criteria = self.present_criteria(
            evaluation_result.get(
                "criteria",
                [],
            )
        )

        return {
            "rubric_type": evaluation_result.get(
                "rubric_type",
                self.rubric_type,
            ),
            "rubric_name": evaluation_result.get(
                "rubric_name",
                self.rubric["name"],
            ),
            "rubric_version": evaluation_result.get(
                "rubric_version",
                self.rubric.get(
                    "version",
                    "1.0",
                ),
            ),
            "global_result": {
                "percentage": global_result.get(
                    "percentage",
                    0.0,
                ),
                "classification": global_result.get(
                    "classification",
                    "Deficiente",
                ),
                "classification_before_critical_rules": (
                    global_result.get(
                        "classification_before_critical_rules",
                        global_result.get(
                            "classification",
                            "Deficiente",
                        ),
                    )
                ),
                "coverage": global_result.get(
                    "coverage",
                    {
                        "percentage": 0.0,
                        "label": "Sin cobertura",
                    },
                ),
                "applicable_indicators": global_result.get(
                    "applicable_indicators",
                    0,
                ),
                "not_applicable_indicators": (
                    global_result.get(
                        "not_applicable_indicators",
                        0,
                    )
                ),
                "total_indicators": global_result.get(
                    "total_indicators",
                    0,
                ),
            },
            "criteria": criteria,
            "strengths": self._build_strengths(
                criteria
            ),
            "improvement_opportunities": (
                self._build_improvements(
                    criteria
                )
            ),
            "critical_alerts": (
                self._sanitize_critical_alerts(
                    evaluation_result.get(
                        "critical_alerts",
                        [],
                    )
                )
            ),
            "executive_summary": (
                evaluation_result.get(
                    "executive_summary",
                    "",
                )
            ),
        }

    def present_turn(
        self,
        *,
        turn_number: int,
        evaluation_result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Presenta el resultado de un turno específico.
        """

        if turn_number <= 0:
            raise ValueError(
                "El número del turno debe ser mayor que cero."
            )

        presented = self.present_evaluation(
            evaluation_result
        )

        return {
            "turn_number": turn_number,
            **presented,
        }

    # ========================================================
    # PROMEDIO LONGITUDINAL DE CRITERIO
    # ========================================================

    def present_criterion_average(
        self,
        *,
        criterion_code: str,
        turn_percentages: list[float | None],
    ) -> dict[str, Any]:
        """
        Presenta el promedio de un criterio a lo largo de varios
        turnos.

        Los valores None no se incluyen en el promedio.
        """

        if criterion_code not in self.criteria_by_code:
            raise ValueError(
                f"Criterio desconocido: {criterion_code}"
            )

        rubric_criterion = self.criteria_by_code[
            criterion_code
        ]

        valid_percentages = [
            float(value)
            for value in turn_percentages
            if value is not None
        ]

        if not valid_percentages:
            return {
                "criterion_code": criterion_code,
                "criterion_name": (
                    rubric_criterion["name"]
                ),
                "order": rubric_criterion.get(
                    "order",
                    0,
                ),
                "turn_percentages": turn_percentages,
                "average_percentage": None,
                "average_score_0_to_3": None,
                "rubric_level": None,
                "level_description": "No evaluable",
                "status": "No evaluable",
            }

        average_percentage = round(
            sum(valid_percentages)
            / len(valid_percentages),
            2,
        )

        average_score_0_to_3 = round(
            (average_percentage / 100) * 3,
            2,
        )

        rubric_level = self._score_to_level(
            average_score_0_to_3
        )

        return {
            "criterion_code": criterion_code,
            "criterion_name": (
                rubric_criterion["name"]
            ),
            "order": rubric_criterion.get(
                "order",
                0,
            ),
            "turn_percentages": turn_percentages,
            "average_percentage": average_percentage,
            "average_score_0_to_3": (
                average_score_0_to_3
            ),
            "rubric_level": rubric_level,
            "level_description": rubric_criterion[
                "levels"
            ][str(rubric_level)],
            "status": self._build_status(
                percentage=average_percentage,
                has_critical_failure=False,
            ),
        }

    # ========================================================
    # CONVERSIÓN DEL PUNTAJE 0-3 A NIVEL VISIBLE 0-3
    # ========================================================

    @staticmethod
    def _score_to_level(
        score_0_to_3: float,
    ) -> int:
        """
        Convierte el promedio continuo 0-3 al nivel entero
        oficial más cercano de la rúbrica.

        Umbrales:
        0: [0.00, 0.50)
        1: [0.50, 1.50)
        2: [1.50, 2.50)
        3: [2.50, 3.00]

        Equivalentes aproximadamente a:
        0: 0-16.66 %
        1: 16.67-49.99 %
        2: 50-83.32 %
        3: 83.33-100 %
        """

        if score_0_to_3 < 0 or score_0_to_3 > 3:
            raise ValueError(
                "El puntaje debe estar entre 0 y 3."
            )

        if score_0_to_3 < 0.5:
            return 0

        if score_0_to_3 < 1.5:
            return 1

        if score_0_to_3 < 2.5:
            return 2

        return 3

    @classmethod
    def _criterion_level_label(
        cls,
        rubric_level: int,
    ) -> str:
        """
        Clasificación cualitativa propia del criterio según nivel 0-3.

        0 -> Deficiente
        1 -> Bajo
        2 -> Aceptable
        3 -> Excelente
        """

        if rubric_level not in cls.CRITERION_LEVEL_LABELS:
            raise ValueError(
                f"Nivel de criterio inválido: {rubric_level}"
            )

        return cls.CRITERION_LEVEL_LABELS[rubric_level]


    # ========================================================
    # ESTADO VISIBLE DEL CRITERIO
    # ========================================================

    def _build_status(
        self,
        *,
        percentage: float,
        has_critical_failure: bool,
    ) -> str:
        """
        Asigna una etiqueta visible al criterio.
        """

        if has_critical_failure:
            return "Alerta crítica"

        if percentage >= self.STRENGTH_THRESHOLD:
            return "Fortaleza destacada"

        if percentage >= self.GOOD_THRESHOLD:
            return "Fortaleza"

        if percentage >= self.ACCEPTABLE_THRESHOLD:
            return "Oportunidad de mejora"

        return "Debilidad prioritaria"

    # ========================================================
    # FORTALEZAS
    # ========================================================

    @staticmethod
    def _build_strengths(
        criteria: list[dict[str, Any]],
    ) -> list[str]:
        """
        Genera fortalezas a partir de criterios con 75 % o más.
        """

        eligible = [
            criterion
            for criterion in criteria
            if (
                criterion["percentage"] is not None
                and criterion["percentage"] >= 75
                and not criterion["has_critical_failure"]
            )
        ]

        eligible.sort(
            key=lambda item: item["percentage"],
            reverse=True,
        )

        return [
            (
                f"{criterion['criterion_name']}: "
                f"{criterion['percentage']:.2f}% "
                f"({criterion['status']})."
            )
            for criterion in eligible[:3]
        ]

    # ========================================================
    # OPORTUNIDADES DE MEJORA
    # ========================================================

    @staticmethod
    def _build_improvements(
        criteria: list[dict[str, Any]],
    ) -> list[str]:
        """
        Genera aspectos por mejorar, priorizando fallas críticas
        y criterios con los porcentajes más bajos.
        """

        eligible = [
            criterion
            for criterion in criteria
            if criterion["percentage"] is not None
        ]

        eligible.sort(
            key=lambda item: (
                not item["has_critical_failure"],
                item["percentage"],
            )
        )

        improvements: list[str] = []

        for criterion in eligible:
            if (
                criterion["percentage"] >= 90
                and not criterion["has_critical_failure"]
            ):
                continue

            if criterion["has_critical_failure"]:
                message = (
                    f"{criterion['criterion_name']}: presenta "
                    f"{criterion['critical_failure_count']} "
                    "falla(s) crítica(s) que requieren revisión."
                )

            else:
                message = (
                    f"{criterion['criterion_name']}: "
                    f"{criterion['percentage']:.2f}% "
                    f"({criterion['status']})."
                )

            improvements.append(
                message
            )

            if len(improvements) == 3:
                break

        return improvements