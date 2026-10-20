"""Explicit future integration entrypoints. Does not alter an active runner.

Consumers must retain status, score=None, evidence and technical cause. Never
render BLOCKED as zero or include descriptive pooled percentages as V2 global.
"""
from .anxiety import evaluate_turn as evaluate_anxiety_turn
from .crisis_ni6_v3_bfix import CrisisEvaluator as CrisisEvaluator

RELEASE='EVALIA-FRONTEND-CANDIDATE-20261014-2'
