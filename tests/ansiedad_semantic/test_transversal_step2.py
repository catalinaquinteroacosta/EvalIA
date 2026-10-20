"""Offline regressions: no providers, credentials or databases are loaded."""
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from backend.evaluators.gd import gd81_safe_pipeline as gd
from backend.evaluators.semantic.em.applicability import (
    GENERAL_INDICATORS, UnresolvedApplicabilityError, determine_em_applicability,
)


@dataclass
class Result:
    status: str
    score: int | None


@dataclass
class Report:
    results: dict
    extraction: dict
    component_verification: dict
    classification: dict
    level_verification: dict
    applicability: dict


def test_gd_typed_report_and_nested_results_are_adapted_without_mutation():
    report = Report({'GD5': Result('SCORED', 2)}, {}, {}, {}, {}, {})
    with patch.object(gd, 'run_gd_pipeline', return_value=report), \
         patch.object(gd, 'audit_coherence', return_value={}) as audit, \
         patch.object(gd, 'reconcile_gd567', return_value={}) as reconcile:
        result = gd.run_gd_pipeline_checked(object())
    assert result['raw'] is report
    assert report.results['GD5'].score == 2
    assert reconcile.call_args.args[0] == {'GD5': {'status': 'SCORED', 'score': 2}}
    assert len(audit.call_args.args) == 5


def test_gd_mapping_compatibility_is_preserved():
    report = Report({}, {}, {}, {}, {}, {})
    assert gd._report_mapping(gd._report_mapping(report)) == gd._report_mapping(report)


def test_gd_invalid_return_is_not_a_score():
    with pytest.raises(TypeError):
        gd._report_mapping(None)


@pytest.mark.parametrize('code', sorted(GENERAL_INDICATORS))
def test_em_general_unknown_cannot_be_na(code):
    with pytest.raises(UnresolvedApplicabilityError):
        determine_em_applicability(code, {}, evaluable_emotional_or_experiential_content='unknown')


@pytest.mark.parametrize('missing,different,requires', [
    ('unknown', 'false', 'false'), ('true', 'unknown', 'false'),
    ('true', 'false', 'unknown'), ('true', 'unknown', 'unknown'),
])
def test_em9_unresolved_gate_cannot_be_na(missing, different, requires):
    with pytest.raises(UnresolvedApplicabilityError):
        determine_em_applicability('EM9', {
            'important_information_missing': missing,
            'materially_different_interpretations': different,
            'guidance_requires_missing_information': requires,
        })


def test_em9_known_inactive_gate_remains_na():
    assert not determine_em_applicability('EM9', {
        'important_information_missing': 'false',
        'materially_different_interpretations': 'false',
        'guidance_requires_missing_information': 'false',
    }).applicable


def test_em9_known_active_gate_remains_applicable_even_if_behavior_is_missing():
    assert determine_em_applicability('EM9', {
        'important_information_missing': 'true',
        'materially_different_interpretations': 'true',
        'guidance_requires_missing_information': 'false',
    }).applicable
