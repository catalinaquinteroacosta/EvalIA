from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


ScoreValue = Literal[0, 1, 2, 3]


@dataclass
class IndicatorResult:
    """
    Resultado producido por la evaluación automática de un indicador.

    Cada regla de EvalIA debe devolver un objeto de esta clase.
    """

    indicator_code: str
    applicable: bool
    score: ScoreValue | None
    justification: str

    evidence: list[str] = field(default_factory=list)
    positive_checks: list[str] = field(default_factory=list)
    negative_checks: list[str] = field(default_factory=list)
    missing_checks: list[str] = field(default_factory=list)

    confidence: float = 0.0
    rule_version: str = "1.0"

    def __post_init__(self) -> None:
        self.indicator_code = self.indicator_code.strip()
        self.justification = self.justification.strip()

        if not self.indicator_code:
            raise ValueError(
                "El código del indicador no puede estar vacío."
            )

        if not isinstance(self.applicable, bool):
            raise TypeError(
                "'applicable' debe ser verdadero o falso."
            )

        if self.applicable:
            if self.score not in {0, 1, 2, 3}:
                raise ValueError(
                    "Un indicador aplicable debe tener "
                    "una puntuación entre 0 y 3."
                )
        else:
            if self.score is not None:
                raise ValueError(
                    "Un indicador no aplicable debe tener score=None."
                )

        if not self.justification:
            raise ValueError(
                "El resultado debe incluir una justificación."
            )

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "La confianza debe estar entre 0.0 y 1.0."
            )

        self.evidence = self._clean_text_list(self.evidence)
        self.positive_checks = self._clean_text_list(
            self.positive_checks
        )
        self.negative_checks = self._clean_text_list(
            self.negative_checks
        )
        self.missing_checks = self._clean_text_list(
            self.missing_checks
        )

    @staticmethod
    def _clean_text_list(values: list[str]) -> list[str]:
        """
        Elimina valores vacíos, espacios innecesarios y duplicados,
        conservando el orden original.
        """
        cleaned_values: list[str] = []
        seen: set[str] = set()

        for value in values:
            cleaned = str(value).strip()

            if not cleaned or cleaned in seen:
                continue

            cleaned_values.append(cleaned)
            seen.add(cleaned)

        return cleaned_values

    @property
    def passed(self) -> bool | None:
        """
        Conversión auxiliar del resultado a lógica binaria.

        - True: cumplimiento adecuado o alto.
        - False: incumplimiento o cumplimiento bajo.
        - None: indicador no aplicable.
        """
        if not self.applicable:
            return None

        return self.score in {2, 3}

    @property
    def percentage(self) -> float | None:
        """
        Convierte la escala de 0 a 3 en porcentaje.
        """
        if not self.applicable or self.score is None:
            return None

        return round((self.score / 3) * 100, 2)

    def to_evaluation_engine_format(self) -> dict[str, Any]:
        """
        Devuelve solamente la estructura que espera actualmente
        EvaluationEngine.validate_evaluation().
        """
        return {
            "indicator_code": self.indicator_code,
            "applicable": self.applicable,
            "score": self.score,
            "justification": self.justification,
        }

    def to_internal_dict(self) -> dict[str, Any]:
        """
        Devuelve el resultado completo para auditoría, pruebas,
        evidencia y trazabilidad.
        """
        result = asdict(self)
        result["passed"] = self.passed
        result["percentage"] = self.percentage

        return result

    @classmethod
    def not_applicable(
        cls,
        indicator_code: str,
        justification: str,
        *,
        evidence: list[str] | None = None,
        confidence: float = 1.0,
        rule_version: str = "1.0",
    ) -> "IndicatorResult":
        """
        Constructor auxiliar para indicadores que no aplican.
        """
        return cls(
            indicator_code=indicator_code,
            applicable=False,
            score=None,
            justification=justification,
            evidence=evidence or [],
            confidence=confidence,
            rule_version=rule_version,
        )

    @classmethod
    def from_checks(
        cls,
        indicator_code: str,
        *,
        positive_checks: list[str],
        negative_checks: list[str],
        missing_checks: list[str],
        evidence: list[str],
        justification: str,
        confidence: float,
        rule_version: str = "1.0",
    ) -> "IndicatorResult":
        """
        Construye una puntuación de 0 a 3 a partir de las micropruebas
        ejecutadas por la regla.

        Esta función será útil para indicadores con varias condiciones.
        """
        positive_count = len(positive_checks)
        negative_count = len(negative_checks)
        missing_count = len(missing_checks)

        total_checks = (
            positive_count
            + negative_count
            + missing_count
        )

        if total_checks == 0:
            score: ScoreValue = 0
        else:
            raw_ratio = positive_count / total_checks

            if negative_count > positive_count:
                score = 0
            elif raw_ratio >= 0.85:
                score = 3
            elif raw_ratio >= 0.60:
                score = 2
            elif raw_ratio > 0:
                score = 1
            else:
                score = 0

        return cls(
            indicator_code=indicator_code,
            applicable=True,
            score=score,
            justification=justification,
            evidence=evidence,
            positive_checks=positive_checks,
            negative_checks=negative_checks,
            missing_checks=missing_checks,
            confidence=confidence,
            rule_version=rule_version,
        )