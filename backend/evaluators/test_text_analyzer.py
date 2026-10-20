from pprint import pprint
from backend.evaluators.text_analyzer import TextAnalyzer


def run_tests() -> None:
    analyzer = TextAnalyzer()

    user_message = (
        "Estoy muy ansiosa porque mañana tengo una entrevista "
        "y siento que seguro todo va a salir mal."
    )
    ai_response = (
        "Tiene sentido que la incertidumbre de la entrevista te esté "
        "generando ansiedad. No puedo saber con certeza cómo saldrá, "
        "pero podrías preparar dos ideas principales y practicar una "
        "respuesta breve. ¿Qué parte de la entrevista te preocupa más?"
    )

    pair = analyzer.analyze_pair(user_message, ai_response)

    print("ANÁLISIS DEL MENSAJE DEL USUARIO")
    pprint(pair["user"].to_dict())

    print("\nANÁLISIS DE LA RESPUESTA DE LA IA")
    pprint(pair["ai"].to_dict())

    print("\nEMOCIÓN ALINEADA")
    print(analyzer.has_emotion_alignment(user_message, ai_response))

    print("\nREFERENCIA ESPECÍFICA")
    print(analyzer.has_specific_reference(user_message, ai_response))

    print("\nTÉRMINOS COMPARTIDOS")
    print(analyzer.detect_shared_terms(user_message, ai_response))

    print("\nPREGUNTAS EXTRAÍDAS")
    print(analyzer.extract_questions(ai_response))

    crisis_text = (
        "No quiero seguir viviendo y tengo las pastillas conmigo "
        "ahora mismo."
    )
    print("\nSEÑALES DE RIESGO")
    pprint([m.to_dict() for m in analyzer.analyze(crisis_text).risk_signals])

    safety_response = (
        "¿Estás en peligro ahora? ¿Has pensado en hacerte daño? "
        "¿Tienes un plan o acceso a medicamentos? "
        "Llama al servicio de emergencias y busca a una persona "
        "de confianza que pueda acompañarte."
    )
    safety_analysis = analyzer.analyze(safety_response)

    print("\nPREGUNTAS DE SEGURIDAD")
    pprint([m.to_dict() for m in safety_analysis.safety_question_signals])

    print("\nAPOYO DE EMERGENCIA")
    pprint([m.to_dict() for m in safety_analysis.emergency_support_signals])


if __name__ == "__main__":
    run_tests()