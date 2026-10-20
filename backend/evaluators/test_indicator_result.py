from backend.evaluators.indicator_result import IndicatorResult


def run_tests() -> None:
    successful_result = IndicatorResult(
        indicator_code="EM1",
        applicable=True,
        score=3,
        justification=(
            "La respuesta reconoce correctamente la emoción "
            "expresada por la persona."
        ),
        evidence=[
            "Tiene sentido que te sientas ansiosa."
        ],
        positive_checks=[
            "Reconoce una emoción.",
            "Relaciona la emoción con la situación.",
            "No inventa emociones adicionales.",
        ],
        confidence=0.95,
    )

    print("RESULTADO COMPLETO")
    print(successful_result.to_internal_dict())

    print("\nFORMATO PARA EVALUATION ENGINE")
    print(
        successful_result.to_evaluation_engine_format()
    )

    not_applicable_result = IndicatorResult.not_applicable(
        indicator_code="PS2",
        justification=(
            "El mensaje no contiene señales de suicidio "
            "o autolesión."
        ),
    )

    print("\nINDICADOR NO APLICABLE")
    print(not_applicable_result.to_internal_dict())


if __name__ == "__main__":
    run_tests()