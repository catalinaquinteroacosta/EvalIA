from unittest.mock import patch
import pytest
from backend.evaluators import af_family_evaluator as evaluator

USER = {'modifiable_components': [{'description': 'Preparar examen',
    'evidence': {'quote': 'Tengo un examen mañana'},
    'semantic_validation': {'status': 'supported'}}]}

@pytest.mark.parametrize('status, expected', [('not_supported', 0), ('ambiguous', 0), ('supported', None)])
def test_af2_valida_relacion_con_usuario(status, expected):
    semantic = {'stressor_targets': [], 'result_guarantees': [], 'stressor_actions': [{
        'action_description': 'Pedir extracto bancario',
        'target_description': 'Conseguir extracto bancario',
        'initiation_description': 'Escribir al banco',
        'feasibility': 'supported',
        'evidence': {'action_quote': 'Escribe al banco para pedir un extracto',
                     'target_quote': 'pedir un extracto', 'initiation_quote': 'Escribe al banco'},
        'semantic_validation': {'action_target': {'status': 'supported'},
                                'initiation': {'status': 'supported'}}}]}
    with patch.object(evaluator, 'extract_ai_control_action', return_value=semantic), \
         patch('backend.evaluators.semantic.af2_context_alignment.validate_af2_relation',
               return_value={'status': status}), \
         patch.object(evaluator, 'extract_af2_response_review', return_value={
             'reviewed_entire_response': False, 'relevant_recommendations': [],
             'material_contradictions': [], 'unresolved_issues': []}):
        result = evaluator._evaluate_af2_isolated(user_control=USER,
            current_ai='Escribe al banco para pedir un extracto', model='simulado', timeout=10)
    assert result['decision'].score == expected
    assert result['semantic']['stressor_actions'][0]['semantic_validation']['user_alignment']['status'] == status

