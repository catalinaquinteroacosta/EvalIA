
"""Exclusi?n expl?cita y auditada de evidencia CP rechazada."""

from dataclasses import replace


def exclude_rejected_evidence(
    state, verification_indicator, rejected_indices
):
    if state.status != "blocked":
        raise ValueError("Se requiere estado blocked.")

    if not isinstance(rejected_indices, (tuple, list)):
        raise TypeError("Los ?ndices deben ser lista o tupla.")

    if any(
        isinstance(i, bool) or not isinstance(i, int)
        for i in rejected_indices
    ):
        raise ValueError("?ndice inv?lido.")

    if len(set(rejected_indices)) != len(rejected_indices):
        raise ValueError("?ndices duplicados.")

    verdicts = verification_indicator.get(
        "evidence_verdicts", []
    )
    verdict_map = {
        v["evidence_index"]: v for v in verdicts
    }

    blocked = set(state.blocked_evidence_indices)
    rejected = []

    for index in rejected_indices:
        if index not in blocked:
            raise ValueError("?ndice no bloqueado.")

        verdict = verdict_map.get(index)

        if not isinstance(verdict, dict):
            raise ValueError("Veredicto inexistente.")

        if verdict.get("status") != "unsupported":
            raise ValueError(
                "No se permite excluir evidencia supported o ambiguous."
            )

        reason = verdict.get("reason")

        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("Falta motivo del rechazo.")

        rejected.append({
            "evidence_index": index,
            "verdict": "unsupported",
            "reason": reason,
        })

    remaining = blocked - set(rejected_indices)

    # La evidencia unsupported queda excluida del conjunto
    # pendiente, pero permanece trazable en el registro auditado.
    # Excluir evidencia nunca autoriza scoring automaticamente.
    remaining = blocked - set(rejected_indices)

    if not state.blocked_components and not remaining:
        # Sin verificacion independiente adicional, no es seguro
        # convertir el estado a validated.
        return state, tuple(rejected)

    updated = replace(
        state,
        status="blocked",
        blocked_evidence_indices=tuple(sorted(remaining)),
    )
    return updated, tuple(rejected)
