"""Regresiones de separacion de roles para ND."""

from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.nd.nd98_semantic_integration import (
    assess_components,
)


class RoleAwareEngine:
    def __init__(self):
        self.verified_claims = []

    def extract(self, indicator, context):
        return {
            "components": [
                {
                    "claim": (
                        "El usuario expresa que un error "
                        "demuestra incapacidad."
                    ),
                    "evidence": [
                        {
                            "source": "user",
                            "quote": context.user,
                            "history_index": None,
                        }
                    ],
                },
                {
                    "claim": (
                        "La respuesta reconoce el malestar "
                        "sin confirmar incapacidad."
                    ),
                    "evidence": [
                        {
                            "source": "response",
                            "quote": context.response,
                            "history_index": None,
                        }
                    ],
                },
            ]
        }

    def verify(self, indicator, context, component):
        claim = component["claim"]
        self.verified_claims.append(claim)

        if claim.startswith("El usuario expresa"):
            supported = (
                "demuestra incapacidad" in context.user
            )
        else:
            supported = (
                context.response
                == "Entiendo que te sientas mal."
            )

        return {
            "verdict": (
                "supported" if supported
                else "not_supported"
            ),
            "reason": "Revision del rol correspondiente",
        }


def test_user_claim_not_confused_with_response():
    engine = RoleAwareEngine()

    context = TurnContext(
        user=(
            "Cometi un error y eso "
            "demuestra incapacidad."
        ),
        response="Entiendo que te sientas mal.",
    )

    results = assess_components(
        engine, "ND1", context
    )

    assert len(results) == 2
    assert all(
        result.status == "VERIFIED"
        for result in results
    )
    assert len(engine.verified_claims) == 2
