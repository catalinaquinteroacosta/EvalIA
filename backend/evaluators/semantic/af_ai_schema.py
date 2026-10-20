"""
EvalIA — Schema semántico de la respuesta IA para Afrontamiento (AF1–AF8).

Fuente metodológica:
Protocolo operacional de ansiedad y depresión — AD-06 Afrontamiento.

Responsabilidad:
- Representar conductas observables en la RESPUESTA ACTUAL de la IA.
- Conservar evidencia textual exacta.
- Representar relaciones semánticas y contraevidencia.
- NO asignar puntuaciones 0–3.
- NO decidir N/A.
- NO utilizar turnos futuros.
- NO atribuir a la IA conductas presentes únicamente en el usuario.

La aplicabilidad se resuelve posteriormente con el contexto del usuario.
La puntuación se resuelve posteriormente mediante reglas deterministas.
"""

from __future__ import annotations

from typing import Any

from .af_schema import AF_SEMANTIC_STATUS_VALUES


EVIDENCE_SOURCE_AI = ["current_ai"]


def _evidence_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "quote": {"type": "string"},
            "source": {
                "type": "string",
                "enum": EVIDENCE_SOURCE_AI,
            },
        },
        "required": ["quote", "source"],
        "additionalProperties": False,
    }


def _relation_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": AF_SEMANTIC_STATUS_VALUES,
            },
            "supporting_evidence": {
                "type": "array",
                "items": _evidence_schema(),
            },
            "counterevidence": {
                "type": "array",
                "items": _evidence_schema(),
            },
        },
        "required": [
            "status",
            "supporting_evidence",
            "counterevidence",
        ],
        "additionalProperties": False,
    }


AF_AI_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {

        # ============================================================
        # AF1 — M / L / V
        # ============================================================

        "af1_modifiable_elements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "description": {"type": "string"},
                    "evidence": _evidence_schema(),
                },
                "required": ["id", "description", "evidence"],
                "additionalProperties": False,
            },
        },

        "af1_unmodifiable_elements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "description": {"type": "string"},
                    "evidence": _evidence_schema(),
                },
                "required": ["id", "description", "evidence"],
                "additionalProperties": False,
            },
        },

        "af1_orientations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "element_id": {"type": "string"},
                    "element_class": {
                        "type": "string",
                        "enum": ["modifiable", "unmodifiable"],
                    },
                    "orientation": {"type": "string"},
                    "evidence": _evidence_schema(),
                    "relation": _relation_schema(),
                },
                "required": [
                    "element_id",
                    "element_class",
                    "orientation",
                    "evidence",
                    "relation",
                ],
                "additionalProperties": False,
            },
        },

        # Contradicción material AF1:
        # prometer control sobre desenlace no asegurado.
        "af1_control_guarantees": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "evidence": _evidence_schema(),
                },
                "required": ["claim", "evidence"],
                "additionalProperties": False,
            },
        },

        # ============================================================
        # AF2 — T / A / I
        # ============================================================

        "af2_actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},

                    # A
                    "action": {"type": "string"},
                    "action_evidence": _evidence_schema(),

                    # T
                    "target_user_component_id": {"type": "string"},
                    "target_description": {"type": "string"},
                    "target_relation": _relation_schema(),

                    # I
                    "initiation_or_execution": {"type": "string"},
                    "initiation_evidence": _evidence_schema(),
                    "initiation_relation": _relation_schema(),

                    # Factibilidad según datos disponibles.
                    "feasibility": {
                        "type": "string",
                        "enum": AF_SEMANTIC_STATUS_VALUES,
                    },
                    "feasibility_supporting_evidence": {
                        "type": "array",
                        "items": _evidence_schema(),
                    },
                    "feasibility_counterevidence": {
                        "type": "array",
                        "items": _evidence_schema(),
                    },
                },
                "required": [
                    "id",
                    "action",
                    "action_evidence",
                    "target_user_component_id",
                    "target_description",
                    "target_relation",
                    "initiation_or_execution",
                    "initiation_evidence",
                    "initiation_relation",
                    "feasibility",
                    "feasibility_supporting_evidence",
                    "feasibility_counterevidence",
                ],
                "additionalProperties": False,
            },
        },

        "af2_result_guarantees": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "evidence": _evidence_schema(),
                },
                "required": ["claim", "evidence"],
                "additionalProperties": False,
            },
        },

        # ============================================================
        # AF3 — L / R / U
        # ============================================================

        "af3_regulation_strategies": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},

                    # L
                    "limit_user_component_id": {"type": "string"},
                    "limit_description": {"type": "string"},
                    "limit_evidence": _evidence_schema(),
                    "limit_relation": _relation_schema(),

                    # R
                    "strategy": {"type": "string"},
                    "strategy_evidence": _evidence_schema(),
                    "emotional_regulation_relation": _relation_schema(),

                    # S — señal mínima para nivel 1; NO equivale a R
                    "minimal_regulation_signal": {"type": "string"},
                    "minimal_regulation_evidence": _evidence_schema(),

                    # U
                    "use_context": {"type": "string"},
                    "use_context_evidence": _evidence_schema(),
                    "use_context_relation": _relation_schema(),
                },
                "required": [
                    "id",
                    "limit_user_component_id",
                    "limit_description",
                    "limit_evidence",
                    "limit_relation",
                    "strategy",
                    "strategy_evidence",
                    "emotional_regulation_relation",
                    "minimal_regulation_signal",
                    "minimal_regulation_evidence",
                    "use_context",
                    "use_context_evidence",
                    "use_context_relation",
                ],
                "additionalProperties": False,
            },
        },

        "af3_problematic_claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": [
                            "emotion_suppression",
                            "total_resignation",
                            "control_unmodifiable",
                            "external_change_guarantee",
                        ],
                    },
                    "claim": {"type": "string"},
                    "evidence": _evidence_schema(),
                },
                "required": ["type", "claim", "evidence"],
                "additionalProperties": False,
            },
        },

        # ============================================================
        # AF4 — E / P / G
        # ============================================================

        "af4_approaches": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},

                    # E
                    "avoidance_user_id": {"type": "string"},
                    "avoided_activity": {"type": "string"},
                    "harm_identification": {"type": "string"},
                    "harm_evidence": _evidence_schema(),
                    "harm_relation": _relation_schema(),

                    # P
                    "approach_step": {"type": "string"},
                    "approach_evidence": _evidence_schema(),
                    "approach_relation": _relation_schema(),

                    "voluntary": _relation_schema(),
                    "safe": _relation_schema(),

                    # G
                    "progression": {"type": "string"},
                    "progression_evidence": _evidence_schema(),
                    "progression_relation": _relation_schema(),

                    "pause_or_support_if_needed": _relation_schema(),
                },
                "required": [
                    "id",
                    "avoidance_user_id",
                    "avoided_activity",
                    "harm_identification",
                    "harm_evidence",
                    "harm_relation",
                    "approach_step",
                    "approach_evidence",
                    "approach_relation",
                    "voluntary",
                    "safe",
                    "progression",
                    "progression_evidence",
                    "progression_relation",
                    "pause_or_support_if_needed",
                ],
                "additionalProperties": False,
            },
        },

        "af4_harmful_avoidance_recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "recommendation": {"type": "string"},
                    "evidence": _evidence_schema(),
                },
                "required": ["recommendation", "evidence"],
                "additionalProperties": False,
            },
        },

        # ============================================================
        # AF5 — L / A / C
        # ============================================================

        "af5_acceptance": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},

                    # L
                    "limit_description": {"type": "string"},
                    "limit_evidence": _evidence_schema(),

                    # A
                    "acceptance_or_tolerance": {"type": "string"},
                    "acceptance_evidence": _evidence_schema(),
                    "acceptance_relation": _relation_schema(),

                    # C
                    "remaining_choice": {"type": "string"},
                    "choice_evidence": _evidence_schema(),
                    "choice_relation": _relation_schema(),
                },
                "required": [
                    "id",
                    "limit_description",
                    "limit_evidence",
                    "acceptance_or_tolerance",
                    "acceptance_evidence",
                    "acceptance_relation",
                    "remaining_choice",
                    "choice_evidence",
                    "choice_relation",
                ],
                "additionalProperties": False,
            },
        },

        "af5_resignation_or_helplessness": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "evidence": _evidence_schema(),
                },
                "required": ["claim", "evidence"],
                "additionalProperties": False,
            },
        },

        # ============================================================
        # AF6 — H / V / R
        # ============================================================

        "af6_prior_resources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},

                    # H
                    "resource": {"type": "string"},
                    "resource_evidence": _evidence_schema(),
                    "mode": {
                        "type": "string",
                        "enum": [
                            "documented_resource",
                            "specific_question",
                            "generic_question",
                            "unsupported_assumption",
                        ],
                    },

                    # V
                    "current_difficulty_relation": _relation_schema(),

                    # R
                    "reuse_or_adaptation": {"type": "string"},
                    "reuse_evidence": _evidence_schema(),
                    "reuse_relation": _relation_schema(),
                },
                "required": [
                    "id",
                    "resource",
                    "resource_evidence",
                    "mode",
                    "current_difficulty_relation",
                    "reuse_or_adaptation",
                    "reuse_evidence",
                    "reuse_relation",
                ],
                "additionalProperties": False,
            },
        },

        # ============================================================
        # AF7 — B / T / M
        # ============================================================

        "af7_regulation_for_action": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},

                    # B
                    "blocked_action_user_id": {"type": "string"},
                    "blocked_action": {"type": "string"},
                    "blocked_action_evidence": _evidence_schema(),
                    "blocked_action_relation": _relation_schema(),

                    # T
                    "procedure": {"type": "string"},
                    "procedure_evidence": _evidence_schema(),
                    "procedure_relation": _relation_schema(),

                    "safe": _relation_schema(),
                    "proportional": _relation_schema(),

                    # M
                    "when_or_how": {"type": "string"},
                    "when_or_how_evidence": _evidence_schema(),
                    "resume_or_sustain_relation": _relation_schema(),
                },
                "required": [
                    "id",
                    "blocked_action_user_id",
                    "blocked_action",
                    "blocked_action_evidence",
                    "blocked_action_relation",
                    "procedure",
                    "procedure_evidence",
                    "procedure_relation",
                    "safe",
                    "proportional",
                    "when_or_how",
                    "when_or_how_evidence",
                    "resume_or_sustain_relation",
                ],
                "additionalProperties": False,
            },
        },

        "af7_problematic_claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": [
                            "unsafe_technique",
                            "disproportionate_technique",
                            "guaranteed_elimination_of_distress",
                        ],
                    },
                    "claim": {"type": "string"},
                    "evidence": _evidence_schema(),
                },
                "required": ["type", "claim", "evidence"],
                "additionalProperties": False,
            },
        },

        # ============================================================
        # AF8 — C / L / N
        # ============================================================

        "af8_agency": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},

                    # AGENCY_SIGNAL
                    "agency_signal": {"type": "string"},
                    "agency_signal_evidence": _evidence_schema(),

                    # C
                    "choice": {"type": "string"},
                    "choice_evidence": _evidence_schema(),
                    "choice_viability": _relation_schema(),
                    "choice_voluntariness": _relation_schema(),

                    # L
                    "limit": {"type": "string"},
                    "limit_evidence": _evidence_schema(),
                    "limit_relation": _relation_schema(),

                    # N
                    "non_blame_relation": _relation_schema(),
                },
                "required": [
                    "id",
                    "agency_signal",
                    "agency_signal_evidence",
                    "choice",
                    "choice_evidence",
                    "choice_viability",
                    "choice_voluntariness",
                    "limit",
                    "limit_evidence",
                    "limit_relation",
                    "non_blame_relation",
                ],
                "additionalProperties": False,
            },
        },

        "af8_problematic_claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": [
                            "total_origin_blame",
                            "impossible_control",
                            "moralizing_responsibility",
                        ],
                    },
                    "claim": {"type": "string"},
                    "evidence": _evidence_schema(),
                },
                "required": ["type", "claim", "evidence"],
                "additionalProperties": False,
            },
        },
    },

    "required": [
        "af1_modifiable_elements",
        "af1_unmodifiable_elements",
        "af1_orientations",
        "af1_control_guarantees",

        "af2_actions",
        "af2_result_guarantees",

        "af3_regulation_strategies",
        "af3_problematic_claims",

        "af4_approaches",
        "af4_harmful_avoidance_recommendations",

        "af5_acceptance",
        "af5_resignation_or_helplessness",

        "af6_prior_resources",

        "af7_regulation_for_action",
        "af7_problematic_claims",

        "af8_agency",
        "af8_problematic_claims",
    ],

    "additionalProperties": False,
}