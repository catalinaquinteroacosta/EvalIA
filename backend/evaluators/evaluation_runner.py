from __future__ import annotations

from importlib import import_module
from typing import Any

from backend.evaluation_engine import EvaluationEngine
from backend.evaluators.criterion_presenter import CriterionPresenter
from backend.evaluators.evaluation_context import EvaluationContext
from backend.evaluators.indicator_result import IndicatorResult
from backend.evaluators.rule_registry import rule_registry
from backend.rubric_loader import normalize_rubric_type


# ============================================================
# MÓDULOS QUE REGISTRAN LAS REGLAS FINALES DE EVALIA
# ============================================================

RULE_MODULES: tuple[str, ...] = (
    # Ansiedad / depresión
    "backend.evaluators.rules.afrontamiento_rules",
    "backend.evaluators.rules.claridad_estructura_rules",
    "backend.evaluators.rules.comprehension_rules",
    "backend.evaluators.rules.dependency_rules",
    "backend.evaluators.rules.distortion_rules",
    "backend.evaluators.rules.empathy_rules",
    "backend.evaluators.rules.participation_safety_rules",
    "backend.evaluators.rules.proposal_action_rules",
    "backend.evaluators.rules.restructuring_rules",

    # Crisis
    "backend.evaluators.rules.crisis_clarity_rules",
    "backend.evaluators.rules.crisis_comprehension_rules",
    "backend.evaluators.rules.crisis_concrete_actions_rules",
    "backend.evaluators.rules.crisis_containment_rules",
    "backend.evaluators.rules.crisis_dependency_autonomy_rules",
    "backend.evaluators.rules.crisis_emotional_restoration_rules",
    "backend.evaluators.rules.crisis_immediate_needs_rules",
    "backend.evaluators.rules.crisis_orientation_psychoeducation_rules",
    "backend.evaluators.rules.crisis_problem_prioritization_rules",
    "backend.evaluators.rules.crisis_risk_rules",
)


SUPPORTED_RUBRICS: frozenset[str] = frozenset(
    {
        "ansiedad_depresion",
        "crisis",
    }
)


EXPECTED_INDICATOR_COUNTS: dict[str, int] = {
    "ansiedad_depresion": 81,
    "crisis": 104,
}


def load_rule_modules() -> None:
    """
    Importa todos los módulos que contienen reglas finales.

    Los decoradores @indicator_rule(...) registran las reglas
    automáticamente en el RuleRegistry global.
    """
    for module_name in RULE_MODULES:
        import_module(module_name)


class EvaluationRunner:
    """
    Orquestador determinístico del motor de evaluación de EvalIA.

    Flujo:
        EvaluationContext
            -> RuleRegistry
            -> IndicatorResult
            -> EvaluationEngine
            -> CriterionPresenter
            -> Resultado visible por criterios

    Los indicadores operacionales permanecen internos.
    """

    def __init__(self, rubric_type: str) -> None:
        normalized_rubric_type = normalize_rubric_type(
            rubric_type
        )

        if normalized_rubric_type not in SUPPORTED_RUBRICS:
            raise ValueError(
                "Rúbrica no soportada por EvaluationRunner: "
                f"'{normalized_rubric_type}'. "
                "Valores permitidos: "
                "'ansiedad_depresion' y 'crisis'."
            )

        self.rubric_type = normalized_rubric_type

        # Los módulos deben cargarse antes de validar
        # la cobertura del registro.
        load_rule_modules()

        self.engine = EvaluationEngine(
            rubric_type=self.rubric_type
        )

        self.presenter = CriterionPresenter(
            rubric_type=self.rubric_type
        )

        self.expected_indicator_codes = (
            self._get_expected_indicator_codes()
        )

        self._validate_rule_registry()

    # ========================================================
    # VALIDACIÓN DE INTEGRIDAD
    # ========================================================

    def _get_expected_indicator_codes(self) -> list[str]:
        """
        Obtiene los indicadores directamente desde la rúbrica
        cargada por EvaluationEngine.

        El JSON continúa siendo la fuente de verdad del mapeo
        criterio -> indicadores.
        """
        codes = list(
            self.engine.indicators_by_code.keys()
        )

        if not codes:
            raise ValueError(
                f"La rúbrica '{self.rubric_type}' "
                "no contiene indicadores."
            )

        expected_count = EXPECTED_INDICATOR_COUNTS[
            self.rubric_type
        ]

        if len(codes) != expected_count:
            raise ValueError(
                f"La rúbrica '{self.rubric_type}' debería "
                f"contener {expected_count} indicadores, "
                f"pero contiene {len(codes)}."
            )

        return codes

    def _validate_rule_registry(self) -> None:
        """
        Comprueba que todos los indicadores requeridos por
        la rúbrica tengan una regla determinística registrada.

        No usa validate_complete(), porque el registro es global
        y contiene reglas pertenecientes a ambas rúbricas.
        """
        missing_codes = rule_registry.missing_codes(
            self.expected_indicator_codes
        )

        if missing_codes:
            raise ValueError(
                "Faltan reglas determinísticas para la rúbrica "
                f"'{self.rubric_type}': "
                + ", ".join(missing_codes)
            )

    # ========================================================
    # EJECUCIÓN INTERNA
    # ========================================================

    def _execute_indicators(
        self,
        context: EvaluationContext,
        turn_number: int | None,
    ) -> list[IndicatorResult]:
        """
        Ejecuta todos los indicadores correspondientes
        a la rúbrica seleccionada.

        turn_number:
        - int  -> evaluación de un turno.
        - None -> evaluación longitudinal.
        """
        if not isinstance(context, EvaluationContext):
            raise TypeError(
                "context debe ser una instancia de "
                "EvaluationContext."
            )

        context_rubric_type = (
            context.rubric_type.strip().lower()
        )

        if context_rubric_type != self.rubric_type:
            raise ValueError(
                "La rúbrica del EvaluationContext no coincide "
                "con la del EvaluationRunner. "
                f"Contexto='{context.rubric_type}', "
                f"Runner='{self.rubric_type}'."
            )

        results = rule_registry.execute_many(
            indicator_codes=self.expected_indicator_codes,
            context=context,
            turn_number=turn_number,
        )

        if len(results) != len(
            self.expected_indicator_codes
        ):
            raise RuntimeError(
                "El RuleRegistry devolvió una cantidad "
                "inesperada de resultados."
            )

        returned_codes = [
            result.indicator_code
            for result in results
        ]

        if returned_codes != self.expected_indicator_codes:
            raise RuntimeError(
                "El orden o los códigos devueltos por las reglas "
                "no coinciden con la rúbrica."
            )

        return results

    @staticmethod
    def _build_engine_payload(
        indicator_results: list[IndicatorResult],
    ) -> dict[str, Any]:
        """
        Convierte los IndicatorResult al formato exacto
        requerido por EvaluationEngine.validate_evaluation().
        """
        return {
            "indicators": [
                result.to_evaluation_engine_format()
                for result in indicator_results
            ]
        }

    def _evaluate_internal(
        self,
        context: EvaluationContext,
        turn_number: int | None,
    ) -> tuple[
        dict[str, Any],
        list[IndicatorResult],
    ]:
        """
        Ejecuta:
        reglas -> IndicatorResult -> EvaluationEngine.

        Devuelve el resultado agregado del motor y los
        IndicatorResult completos para auditoría interna.
        """
        indicator_results = self._execute_indicators(
            context=context,
            turn_number=turn_number,
        )

        engine_payload = self._build_engine_payload(
            indicator_results
        )

        engine_result = self.engine.validate_evaluation(
            engine_payload
        )

        return engine_result, indicator_results

    # ========================================================
    # EVALUACIÓN DE UN TURNO
    # ========================================================

    def evaluate_turn_internal(
        self,
        context: EvaluationContext,
        turn_number: int,
    ) -> dict[str, Any]:
        """
        Evalúa un turno conservando los indicadores completos.

        Esta salida es para auditoría/persistencia técnica.
        No debe enviarse directamente al frontend.
        """
        if not isinstance(turn_number, int):
            raise TypeError(
                "turn_number debe ser un entero."
            )

        # También valida que el turno exista.
        context.get_turn(turn_number)

        engine_result, indicator_results = (
            self._evaluate_internal(
                context=context,
                turn_number=turn_number,
            )
        )

        return {
            "rubric_type": self.rubric_type,
            "turn_number": turn_number,
            "evaluation": engine_result,
            "indicator_results": [
                result.to_internal_dict()
                for result in indicator_results
            ],
        }

    def evaluate_turn(
        self,
        context: EvaluationContext,
        turn_number: int,
    ) -> dict[str, Any]:
        """
        Evalúa un turno y devuelve exclusivamente la
        representación preparada para frontend.
        """
        if not isinstance(turn_number, int):
            raise TypeError(
                "turn_number debe ser un entero."
            )

        context.get_turn(turn_number)

        engine_result, _ = self._evaluate_internal(
            context=context,
            turn_number=turn_number,
        )

        # Firma real de CriterionPresenter:
        # present_turn(
        #     *,
        #     turn_number: int,
        #     evaluation_result: dict
        # )
        return self.presenter.present_turn(
            turn_number=turn_number,
            evaluation_result=engine_result,
        )

    # ========================================================
    # EVALUACIÓN LONGITUDINAL
    # ========================================================

    def evaluate_conversation_internal(
        self,
        context: EvaluationContext,
    ) -> dict[str, Any]:
        """
        Ejecuta la evaluación acumulada de toda la conversación
        conservando los indicadores para auditoría.
        """
        engine_result, indicator_results = (
            self._evaluate_internal(
                context=context,
                turn_number=None,
            )
        )

        return {
            "rubric_type": self.rubric_type,
            "evaluation_scope": "conversation",
            "evaluation": engine_result,
            "indicator_results": [
                result.to_internal_dict()
                for result in indicator_results
            ],
        }

    def evaluate_conversation(
        self,
        context: EvaluationContext,
    ) -> dict[str, Any]:
        """
        Evalúa longitudinalmente toda la conversación y devuelve
        únicamente la representación visible por criterios.

        Las preguntas operacionales no se exponen.
        """
        engine_result, _ = self._evaluate_internal(
            context=context,
            turn_number=None,
        )

        # Firma real:
        # present_evaluation(evaluation_result)
        return self.presenter.present_evaluation(
            evaluation_result=engine_result
        )

    # ========================================================
    # EVALUACIÓN COMPLETA DEL EXPERIMENTO
    # ========================================================

    def evaluate_all_turns(
        self,
        context: EvaluationContext,
    ) -> list[dict[str, Any]]:
        """
        Evalúa individualmente todos los turnos existentes.
        """
        evaluations: list[dict[str, Any]] = []

        for turn in context.turns:
            evaluations.append(
                self.evaluate_turn(
                    context=context,
                    turn_number=turn.turn_number,
                )
            )

        return evaluations

    def evaluate_experiment(
        self,
        context: EvaluationContext,
    ) -> dict[str, Any]:
        """
        Ejecuta el flujo visible completo:

        1. evaluación de cada turno;
        2. evaluación longitudinal;
        3. resultado preparado para frontend.

        No expone indicadores operacionales.
        """
        turn_results = self.evaluate_all_turns(
            context=context
        )

        conversation_result = (
            self.evaluate_conversation(
                context=context
            )
        )

        return {
            "rubric_type": self.rubric_type,
            "experiment_id": context.experiment_id,
            "scenario_code": context.scenario_code,
            "model_name": context.model_name,
            "total_turns": len(context.turns),
            "turn_results": turn_results,
            "conversation_result": conversation_result,
        }

    # ========================================================
    # AUDITORÍA
    # ========================================================

    def audit_registry(self) -> dict[str, Any]:
        """
        Devuelve la cobertura técnica de reglas de la
        rúbrica seleccionada.
        """
        missing_codes = rule_registry.missing_codes(
            self.expected_indicator_codes
        )

        registered_for_rubric = [
            code
            for code in self.expected_indicator_codes
            if rule_registry.contains(code)
        ]

        return {
            "rubric_type": self.rubric_type,
            "expected_indicators": len(
                self.expected_indicator_codes
            ),
            "registered_indicators": len(
                registered_for_rubric
            ),
            "missing_indicators": missing_codes,
            "complete": not missing_codes,
            "global_registry_total": (
                rule_registry.total_rules
            ),
        }