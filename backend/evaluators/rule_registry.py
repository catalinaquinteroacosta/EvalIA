from __future__ import annotations

from collections.abc import Callable
from typing import Any

from backend.evaluators.evaluation_context import (
    EvaluationContext,
)
from backend.evaluators.indicator_result import (
    IndicatorResult,
)


IndicatorRule = Callable[
    [EvaluationContext, int | None],
    IndicatorResult,
]


class RuleRegistry:
    """
    Registro central de reglas automáticas de EvalIA.

    Cada indicador debe estar asociado a una única función evaluadora.
    El registro permite:

    - registrar reglas;
    - impedir códigos duplicados;
    - consultar una regla;
    - ejecutar reglas;
    - verificar indicadores faltantes;
    - garantizar que todas devuelvan IndicatorResult.
    """

    def __init__(self) -> None:
        self._rules: dict[str, IndicatorRule] = {}

    def register(
        self,
        indicator_code: str,
        rule: IndicatorRule,
    ) -> None:
        """
        Registra una regla para un indicador.

        No permite registrar dos reglas con el mismo código.
        """

        normalized_code = self._normalize_code(
            indicator_code
        )

        if not callable(rule):
            raise TypeError(
                f"La regla de '{normalized_code}' "
                "debe ser una función ejecutable."
            )

        if normalized_code in self._rules:
            raise ValueError(
                f"Ya existe una regla registrada para "
                f"'{normalized_code}'."
            )

        self._rules[normalized_code] = rule

    def register_many(
        self,
        rules: dict[str, IndicatorRule],
    ) -> None:
        """
        Registra varias reglas mediante un diccionario:

        {
            "EM1": evaluate_em1,
            "EM2": evaluate_em2,
        }
        """

        if not isinstance(rules, dict):
            raise TypeError(
                "'rules' debe ser un diccionario."
            )

        for indicator_code, rule in rules.items():
            self.register(
                indicator_code=indicator_code,
                rule=rule,
            )

    def get(
        self,
        indicator_code: str,
    ) -> IndicatorRule:
        """
        Obtiene la regla asociada a un indicador.
        """

        normalized_code = self._normalize_code(
            indicator_code
        )

        try:
            return self._rules[normalized_code]
        except KeyError as error:
            raise KeyError(
                f"No existe una regla registrada para "
                f"'{normalized_code}'."
            ) from error

    def execute(
        self,
        indicator_code: str,
        context: EvaluationContext,
        turn_number: int | None = None,
    ) -> IndicatorResult:
        """
        Ejecuta la regla de un indicador.

        turn_number:
        - entero: evaluación de un turno específico;
        - None: evaluación global de la conversación.
        """

        if not isinstance(
            context,
            EvaluationContext,
        ):
            raise TypeError(
                "'context' debe ser una instancia "
                "de EvaluationContext."
            )

        if (
            turn_number is not None
            and turn_number <= 0
        ):
            raise ValueError(
                "El número del turno debe ser mayor "
                "que cero."
            )

        if turn_number is not None:
            context.get_turn(turn_number)

        rule = self.get(indicator_code)

        result = rule(
            context,
            turn_number,
        )

        if not isinstance(
            result,
            IndicatorResult,
        ):
            raise TypeError(
                f"La regla de '{indicator_code}' "
                "debe devolver IndicatorResult."
            )

        expected_code = self._normalize_code(
            indicator_code
        )

        returned_code = self._normalize_code(
            result.indicator_code
        )

        if returned_code != expected_code:
            raise ValueError(
                f"La regla registrada como "
                f"'{expected_code}' devolvió el código "
                f"'{returned_code}'."
            )

        return result

    def execute_many(
        self,
        indicator_codes: list[str],
        context: EvaluationContext,
        turn_number: int | None = None,
    ) -> list[IndicatorResult]:
        """
        Ejecuta varias reglas conservando el orden recibido.
        """

        if not isinstance(
            indicator_codes,
            list,
        ):
            raise TypeError(
                "'indicator_codes' debe ser una lista."
            )

        results: list[IndicatorResult] = []

        for indicator_code in indicator_codes:
            results.append(
                self.execute(
                    indicator_code=indicator_code,
                    context=context,
                    turn_number=turn_number,
                )
            )

        return results

    def contains(
        self,
        indicator_code: str,
    ) -> bool:
        """
        Indica si ya existe una regla registrada.
        """

        normalized_code = self._normalize_code(
            indicator_code
        )

        return normalized_code in self._rules

    def missing_codes(
        self,
        expected_codes: list[str] | set[str],
    ) -> list[str]:
        """
        Devuelve los códigos esperados que todavía no tienen regla.
        """

        normalized_expected = {
            self._normalize_code(code)
            for code in expected_codes
        }

        return sorted(
            normalized_expected.difference(
                self._rules.keys()
            )
        )

    def extra_codes(
        self,
        expected_codes: list[str] | set[str],
    ) -> list[str]:
        """
        Devuelve reglas registradas que no aparecen en la lista
        esperada.
        """

        normalized_expected = {
            self._normalize_code(code)
            for code in expected_codes
        }

        return sorted(
            set(self._rules.keys()).difference(
                normalized_expected
            )
        )

    def validate_complete(
        self,
        expected_codes: list[str] | set[str],
    ) -> None:
        """
        Verifica que el registro coincida exactamente con los
        indicadores esperados.
        """

        missing = self.missing_codes(
            expected_codes
        )
        extra = self.extra_codes(
            expected_codes
        )

        problems: list[str] = []

        if missing:
            problems.append(
                "Faltan reglas para: "
                + ", ".join(missing)
            )

        if extra:
            problems.append(
                "Existen reglas no esperadas para: "
                + ", ".join(extra)
            )

        if problems:
            raise ValueError(
                "Registro de reglas incompleto o "
                "inconsistente. "
                + " ".join(problems)
            )

    @property
    def registered_codes(self) -> list[str]:
        """
        Devuelve todos los códigos registrados.
        """

        return sorted(self._rules.keys())

    @property
    def total_rules(self) -> int:
        return len(self._rules)

    def clear(self) -> None:
        """
        Elimina todas las reglas registradas.

        Se usará principalmente en pruebas.
        """

        self._rules.clear()

    @staticmethod
    def _normalize_code(
        indicator_code: str,
    ) -> str:
        if not isinstance(
            indicator_code,
            str,
        ):
            raise TypeError(
                "El código del indicador debe ser "
                "una cadena de texto."
            )

        normalized_code = (
            indicator_code
            .strip()
            .upper()
        )

        if not normalized_code:
            raise ValueError(
                "El código del indicador no puede "
                "estar vacío."
            )

        return normalized_code


rule_registry = RuleRegistry()


def indicator_rule(
    indicator_code: str,
) -> Callable[
    [IndicatorRule],
    IndicatorRule,
]:
    """
    Decorador para registrar reglas automáticamente.

    Ejemplo:

    @indicator_rule("EM1")
    def evaluate_em1(
        context: EvaluationContext,
        turn_number: int | None,
    ) -> IndicatorResult:
        ...
    """

    def decorator(
        function: IndicatorRule,
    ) -> IndicatorRule:
        rule_registry.register(
            indicator_code=indicator_code,
            rule=function,
        )

        return function

    return decorator