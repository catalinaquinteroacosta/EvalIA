import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent
RUBRICS_DIR = BASE_DIR / "database" / "rubrics"

VALID_LEVEL_KEYS = {"0", "1", "2", "3"}

VALID_INDICATOR_TYPES = {
    "Constructo",
    "Constructo psicológico",
    "Guardrail",
    "Híbrido",
    "Calidad comunicativa",
}

VALID_CRITICALITIES = {
    "Bajo",
    "Medio",
    "Alto",
    "Crítico",
}

VALID_APPLICABILITY_VALUES = {
    "general",
    "conditional",
}

VALID_PRIORITIES = {
    "normal",
    "critical_priority",
}


def normalize_rubric_type(rubric_type: str) -> str:
    """
    Normaliza el identificador de una rúbrica.

    Ejemplos:
    - " Crisis " -> "crisis"
    - "Ansiedad_Depresion" -> "ansiedad_depresion"
    """
    if not isinstance(rubric_type, str):
        raise TypeError(
            "rubric_type debe ser una cadena de texto."
        )

    normalized_type = rubric_type.strip().lower()

    if not normalized_type:
        raise ValueError(
            "rubric_type no puede estar vacío."
        )

    return normalized_type


def load_rubric(
    rubric_type: str,
) -> dict[str, Any] | None:
    """
    Carga y valida una rúbrica desde un archivo JSON.

    Ejemplos:
    - ansiedad_depresion
    - crisis

    La función retorna None cuando el archivo no existe.
    Si el archivo existe pero su estructura es inválida,
    genera una excepción descriptiva.
    """
    normalized_type = normalize_rubric_type(
        rubric_type
    )

    file_path = (
        RUBRICS_DIR
        / f"{normalized_type}.json"
    )

    if not file_path.exists():
        return None

    if not file_path.is_file():
        raise ValueError(
            f"La ruta de la rúbrica "
            f"'{file_path.name}' no corresponde "
            "a un archivo válido."
        )

    try:
        with file_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            rubric = json.load(file)

    except json.JSONDecodeError as error:
        raise ValueError(
            f"El archivo de rúbrica "
            f"'{file_path.name}' contiene "
            f"JSON inválido en la línea "
            f"{error.lineno}, columna "
            f"{error.colno}."
        ) from error

    except OSError as error:
        raise OSError(
            f"No fue posible leer la rúbrica "
            f"'{file_path.name}'."
        ) from error

    validate_rubric(
        rubric=rubric,
        expected_rubric_type=normalized_type,
    )

    return rubric


def validate_rubric(
    rubric: dict[str, Any],
    expected_rubric_type: str | None = None,
) -> None:
    """
    Verifica que la rúbrica contenga la estructura
    necesaria para funcionar con EvaluationEngine.
    """
    if not isinstance(rubric, dict):
        raise ValueError(
            "La rúbrica debe ser un objeto JSON."
        )

    required_fields = {
        "rubric_type",
        "name",
        "applicable_categories",
        "scale",
        "criteria",
    }

    missing_fields = required_fields.difference(
        rubric.keys()
    )

    if missing_fields:
        raise ValueError(
            "La rúbrica no contiene los campos "
            "obligatorios: "
            + ", ".join(sorted(missing_fields))
        )

    rubric_type = rubric.get("rubric_type")

    if not isinstance(rubric_type, str):
        raise ValueError(
            "'rubric_type' debe ser una cadena."
        )

    normalized_rubric_type = (
        rubric_type.strip().lower()
    )

    if not normalized_rubric_type:
        raise ValueError(
            "'rubric_type' no puede estar vacío."
        )

    if (
        expected_rubric_type is not None
        and normalized_rubric_type
        != expected_rubric_type
    ):
        raise ValueError(
            "El rubric_type interno "
            f"'{normalized_rubric_type}' no "
            "coincide con el archivo solicitado "
            f"'{expected_rubric_type}.json'."
        )

    name = rubric.get("name")

    if (
        not isinstance(name, str)
        or not name.strip()
    ):
        raise ValueError(
            "'name' debe contener el nombre "
            "de la rúbrica."
        )

    applicable_categories = rubric.get(
        "applicable_categories"
    )

    if (
        not isinstance(
            applicable_categories,
            list,
        )
        or not applicable_categories
    ):
        raise ValueError(
            "'applicable_categories' debe "
            "contener una lista no vacía."
        )

    for category in applicable_categories:
        if (
            not isinstance(category, str)
            or not category.strip()
        ):
            raise ValueError(
                "Todas las categorías aplicables "
                "deben ser cadenas no vacías."
            )

    validate_scale(rubric["scale"])

    criteria = rubric.get("criteria")

    if (
        not isinstance(criteria, list)
        or not criteria
    ):
        raise ValueError(
            "La rúbrica debe contener una "
            "lista no vacía de criterios."
        )

    criterion_codes: set[str] = set()
    indicator_codes: set[str] = set()

    for index, criterion in enumerate(
        criteria,
        start=1,
    ):
        validate_criterion(
            criterion=criterion,
            index=index,
            criterion_codes=criterion_codes,
            indicator_codes=indicator_codes,
        )


def validate_scale(
    scale: dict[str, Any],
) -> None:
    """
    Verifica la escala global de evaluación.
    """
    if not isinstance(scale, dict):
        raise ValueError(
            "'scale' debe ser un objeto."
        )

    minimum = scale.get("minimum")
    maximum = scale.get("maximum")
    labels = scale.get("labels")

    if minimum != 0 or maximum != 3:
        raise ValueError(
            "La escala debe tener mínimo 0 "
            "y máximo 3."
        )

    if not isinstance(labels, dict):
        raise ValueError(
            "'scale.labels' debe ser un objeto."
        )

    if set(labels.keys()) != VALID_LEVEL_KEYS:
        raise ValueError(
            "'scale.labels' debe contener "
            "exactamente los niveles "
            "0, 1, 2 y 3."
        )

    for level, label in labels.items():
        if (
            not isinstance(label, str)
            or not label.strip()
        ):
            raise ValueError(
                f"La etiqueta del nivel "
                f"'{level}' no puede estar vacía."
            )


def validate_criterion(
    criterion: dict[str, Any],
    index: int,
    criterion_codes: set[str],
    indicator_codes: set[str],
) -> None:
    """
    Valida un criterio y todos sus indicadores.
    """
    if not isinstance(criterion, dict):
        raise ValueError(
            f"El criterio número {index} "
            "debe ser un objeto."
        )

    required_fields = {
        "code",
        "name",
        "levels",
        "indicators",
    }

    missing_fields = required_fields.difference(
        criterion.keys()
    )

    if missing_fields:
        raise ValueError(
            f"El criterio número {index} "
            "no contiene los campos: "
            + ", ".join(sorted(missing_fields))
        )

    criterion_code = str(
        criterion.get("code", "")
    ).strip()

    if not criterion_code:
        raise ValueError(
            f"El criterio número {index} "
            "no contiene un código válido."
        )

    if criterion_code in criterion_codes:
        raise ValueError(
            f"Código de criterio duplicado: "
            f"{criterion_code}"
        )

    criterion_codes.add(criterion_code)

    criterion_name = criterion.get("name")

    if (
        not isinstance(criterion_name, str)
        or not criterion_name.strip()
    ):
        raise ValueError(
            f"El criterio '{criterion_code}' "
            "no contiene un nombre válido."
        )

    levels = criterion.get("levels")

    if not isinstance(levels, dict):
        raise ValueError(
            f"Los niveles del criterio "
            f"'{criterion_code}' deben ser "
            "un objeto."
        )

    if set(levels.keys()) != VALID_LEVEL_KEYS:
        raise ValueError(
            f"El criterio '{criterion_code}' "
            "debe contener exactamente los "
            "niveles 0, 1, 2 y 3."
        )

    for level, description in levels.items():
        if (
            not isinstance(description, str)
            or not description.strip()
        ):
            raise ValueError(
                f"El nivel '{level}' del "
                f"criterio '{criterion_code}' "
                "no contiene una descripción "
                "válida."
            )

    indicators = criterion.get("indicators")

    if (
        not isinstance(indicators, list)
        or not indicators
    ):
        raise ValueError(
            f"El criterio '{criterion_code}' "
            "debe contener una lista no vacía "
            "de indicadores."
        )

    for indicator_index, indicator in enumerate(
        indicators,
        start=1,
    ):
        validate_indicator(
            indicator=indicator,
            criterion_code=criterion_code,
            indicator_index=indicator_index,
            indicator_codes=indicator_codes,
        )


def validate_indicator(
    indicator: dict[str, Any],
    criterion_code: str,
    indicator_index: int,
    indicator_codes: set[str],
) -> None:
    """
    Valida un indicador interno de la rúbrica.
    """
    if not isinstance(indicator, dict):
        raise ValueError(
            f"El indicador número "
            f"{indicator_index} del criterio "
            f"'{criterion_code}' debe ser "
            "un objeto."
        )

    required_fields = {
        "code",
        "question",
        "type",
        "criticality",
    }

    missing_fields = required_fields.difference(
        indicator.keys()
    )

    if missing_fields:
        raise ValueError(
            f"El indicador número "
            f"{indicator_index} del criterio "
            f"'{criterion_code}' no contiene: "
            + ", ".join(sorted(missing_fields))
        )

    indicator_code = str(
        indicator.get("code", "")
    ).strip()

    if not indicator_code:
        raise ValueError(
            f"Existe un indicador sin código "
            f"en el criterio '{criterion_code}'."
        )

    if indicator_code in indicator_codes:
        raise ValueError(
            f"Código de indicador duplicado: "
            f"{indicator_code}"
        )

    indicator_codes.add(indicator_code)

    question = indicator.get("question")

    if (
        not isinstance(question, str)
        or not question.strip()
    ):
        raise ValueError(
            f"El indicador '{indicator_code}' "
            "no contiene una pregunta válida."
        )

    indicator_type = indicator.get("type")

    if indicator_type not in VALID_INDICATOR_TYPES:
        raise ValueError(
            f"El indicador '{indicator_code}' "
            f"contiene un tipo inválido: "
            f"'{indicator_type}'."
        )

    criticality = indicator.get("criticality")

    if criticality not in VALID_CRITICALITIES:
        raise ValueError(
            f"El indicador '{indicator_code}' "
            f"contiene una criticidad inválida: "
            f"'{criticality}'."
        )

    applicability = indicator.get(
        "applicability",
        "general",
    )

    if applicability not in (
        VALID_APPLICABILITY_VALUES
    ):
        raise ValueError(
            f"El indicador '{indicator_code}' "
            "contiene una aplicabilidad inválida: "
            f"'{applicability}'."
        )

    priority = indicator.get(
        "priority",
        "normal",
    )

    if priority not in VALID_PRIORITIES:
        raise ValueError(
            f"El indicador '{indicator_code}' "
            f"contiene una prioridad inválida: "
            f"'{priority}'."
        )

    if (
        priority == "critical_priority"
        and criticality != "Crítico"
    ):
        raise ValueError(
            f"El indicador '{indicator_code}' "
            "está marcado como prioridad crítica, "
            "pero su criticidad no es 'Crítico'."
        )


def list_available_rubrics() -> list[str]:
    """
    Devuelve los nombres de todas las rúbricas
    JSON disponibles.
    """
    if not RUBRICS_DIR.exists():
        return []

    return sorted(
        file_path.stem
        for file_path in RUBRICS_DIR.glob(
            "*.json"
        )
        if file_path.is_file()
    )


def load_all_rubrics() -> dict[str, dict[str, Any]]:
    """
    Carga y valida todas las rúbricas disponibles.
    """
    loaded_rubrics: dict[
        str,
        dict[str, Any],
    ] = {}

    for rubric_type in list_available_rubrics():
        rubric = load_rubric(rubric_type)

        if rubric is not None:
            loaded_rubrics[rubric_type] = rubric

    return loaded_rubrics


if __name__ == "__main__":
    available_rubrics = (
        list_available_rubrics()
    )

    if not available_rubrics:
        print(
            "No se encontraron rúbricas "
            f"en: {RUBRICS_DIR}"
        )
    else:
        print(
            "Rúbricas disponibles: "
            + ", ".join(available_rubrics)
        )

        for rubric_type in available_rubrics:
            loaded_rubric = load_rubric(
                rubric_type
            )

            if loaded_rubric is None:
                continue

            total_criteria = len(
                loaded_rubric["criteria"]
            )

            total_indicators = sum(
                len(
                    criterion.get(
                        "indicators",
                        [],
                    )
                )
                for criterion in (
                    loaded_rubric["criteria"]
                )
            )

            print(
                f"- {loaded_rubric['name']} "
                f"[{rubric_type}]: "
                f"{total_criteria} criterios, "
                f"{total_indicators} indicadores."
            )