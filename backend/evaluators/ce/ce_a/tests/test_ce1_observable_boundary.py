"""CE1 must verify observable meaning separately from contextual relevance."""
from unittest.mock import patch
import pytest
from backend.evaluators.ce.ce_a import ce1_observable as obs
from backend.evaluators.ce.ce_a import ce1_digression_verifier as dig

@pytest.mark.parametrize('interpretation,evidence,description', [
 ('Recomienda revisar el puesto para la entrevista.', 'revisar la descripción del puesto', 'Recomienda revisar la descripción del puesto.'),
 ('Habla de películas sin abordar la entrevista.', 'las películas de ciencia ficción suelen imaginar entrevistas con robots', 'Comenta que las películas de ciencia ficción suelen imaginar entrevistas con robots.'),
 ('El pan no responde a la entrevista.', 'Para hacer pan casero, mezcla harina, agua y levadura', 'Da instrucciones para preparar pan casero.'),
])
def test_observable_prompt_keeps_contextual_judgment_separate(interpretation,evidence,description):
    with patch.object(obs,'get_semantic_identity',return_value={'model':'mock'}),patch.object(obs,'run_structured_semantic',return_value={'description':description,'reason':'Only quoted content'}) as model:
        out=obs.describe_observable(interpretation,evidence,evidence, use_cache=False)
    assert out['description']==description
    prompt=model.call_args.kwargs['prompt']
    assert 'NO' in prompt and 'UNVERIFIED INTERPRETATION' in prompt
    assert evidence in prompt

def test_original_contextual_assertion_is_not_sent_to_literal_verifier():
    args=dict(interpretation='El pan no responde a la entrevista.',evidence='Para hacer pan casero, mezcla harina, agua y levadura',user_text='¿Cómo preparo la entrevista?',response_text='Para hacer pan casero, mezcla harina, agua y levadura')
    with patch.object(dig,'describe_observable',return_value={'description':'Da instrucciones para preparar pan casero.','reason':'Observed'}),patch.object(dig,'verify_claims',return_value={'verdict':'supported','reason':'Supported'}) as check,patch.object(dig,'get_semantic_identity',return_value={'model':'mock'}),patch.object(dig,'run_structured_semantic',return_value={'verdict':'unnecessary_digression','reason':'Not related to interview'}):
        result=dig.verify_ce1_digression(**args)
    assert check.call_args.args[0]=='Da instrucciones para preparar pan casero.'
    assert result['contextual_verdict']['verdict']=='unnecessary_digression'

def test_unverified_observable_still_blocks_contextual_decision():
    args=dict(interpretation='La respuesta inventa un consejo.',evidence='compra flores',user_text='¿Cómo preparo la entrevista?',response_text='compra flores')
    with patch.object(dig,'describe_observable',return_value={'description':'Inventa un consejo.','reason':'Candidate'}),patch.object(dig,'verify_claims',return_value={'verdict':'not_supported','reason':'Unsupported'}),patch.object(dig,'run_structured_semantic') as semantic:
        result=dig.verify_ce1_digression(**args)
    assert result['status']=='review_required'
    semantic.assert_not_called()
