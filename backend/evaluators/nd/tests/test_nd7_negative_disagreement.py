from unittest.mock import patch

from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.nd import reconciliation


def test_nd7_absence_refuted_must_not_become_na():
    context = TurnContext(
        user="Siempre hago todo mal. Nada funciona.",
        response="Lamento que te sientas as?.",
    )

    class Engine:
        def _run(self, **kwargs):
            return {
                "verdict": "absent",
                "reason": "Ausencia propuesta por reconciliaci?n",
            }

    with patch.object(
        reconciliation,
        "validate_negative_applicability",
        create=True,
        return_value={
            "verdict": "not_supported",
            "reason": "El usuario expresa una visi?n absoluta.",
        },
    ):
        with patch(
            "backend.evaluators.nd.negative_validation."
            "validate_negative_applicability",
            return_value={
                "verdict": "not_supported",
                "reason": "El usuario expresa una visi?n absoluta.",
            },
        ):
            result = reconciliation.reconcile_applicability(
                Engine(),
                "ND7",
                context,
                {
                    "verdict": "present",
                    "reason": "Existe visi?n absoluta.",
                },
                {
                    "verdict": "absent",
                    "reason": "No se detecta condici?n.",
                },
            )

    assert result.status != "NA"
    assert result.status == "BLOCKED"
