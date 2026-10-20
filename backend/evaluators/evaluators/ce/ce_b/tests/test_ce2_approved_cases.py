from backend.evaluators.ce.ce_b.ce2_adjudicated_cases import APPROVED_CASES
from backend.evaluators.ce.ce_b.ce2_scoring import score_ce2


def test_approved_case_registered_without_fabricated_literal_evidence():
    case, = APPROVED_CASES
    assert case.expected_score == 1
    assert 'No quiero consejos' in case.user_text
    assert '[desarrolla' in case.assistant_text  # Esquema, NO transcripción literal


def test_generic_coverage_without_other_defects_maps_to_one():
    assert score_ce2(analysis_complete=True, need_coverage='generic',
                     overload='none', secondary_defect=False,
                     semantic_verified=True)['score'] == 1


def test_combined_generic_coverage_and_obstructive_overload_requires_adjudication():
    result = score_ce2(analysis_complete=True, need_coverage='generic',
                       overload='obstructive', secondary_defect=False,
                       semantic_verified=True)
    assert result == {'status': 'requires_adjudication', 'score': None}
