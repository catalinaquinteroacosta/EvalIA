from backend.evaluators.semantic.em.prompts_v2 import (
    EM_PROMPT_V2_VERSION,
    build_em_extraction_prompt_v2,
)
from backend.evaluators.semantic.em.verifier_v2 import (
    EM_VERIFIER_V2_VERSION,
    build_verification_prompt_v2,
)


def test_extractor_prompt_requires_history_when_claim_depends_on_reference():
    prompt = build_em_extraction_prompt_v2(
        "EM2",
        "Hoy sigo muy angustiada por eso.",
        "Entiendo que sigas sintiendote asi por lo que paso.",
        prior_history=[
            {
                "role": "user",
                "text": (
                    "Ayer me despidieron del trabajo "
                    "sin esperarlo."
                ),
            }
        ],
    )

    assert "RESOLUCION DE REFERENTES" in prompt
    assert (
        'evidencia source="history"'
        in prompt
    )
    assert (
        "NO agregues historial solo"
        in prompt
    )
    assert (
        "La necesidad de resolver un referente es SEMANTICA"
        in prompt
    )


def test_verifier_must_recover_historical_antecedent():
    prompt = build_verification_prompt_v2(
        indicator_code="EM2",
        component_name="experience_understood",
        proposed_value="true",
        evidence=[
            {
                "source": "response",
                "history_index": None,
                "quote": "por lo que paso",
            }
        ],
        counterevidence=[],
        prior_history=[
            {
                "role": "user",
                "text": (
                    "Ayer me despidieron del trabajo "
                    "sin esperarlo."
                ),
            }
        ],
        user_message="Hoy sigo muy angustiada por eso.",
        ai_response=(
            "Entiendo que sigas sintiendote asi "
            "por lo que paso."
        ),
    )

    assert (
        "debes incluir en"
        in prompt
    )
    assert (
        'supporting_evidence la evidencia source="history"'
        in prompt
    )
    assert (
        "resolucion de referentes es semantica"
        in prompt
    )


def test_versions_reference_patch():
    assert EM_PROMPT_V2_VERSION == "EM-PROMPT-2.1.0"
    assert EM_VERIFIER_V2_VERSION == "EM-VERIFIER-2.7.0"
