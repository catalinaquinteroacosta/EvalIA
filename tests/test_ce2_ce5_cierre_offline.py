import json
from pathlib import Path

DATA = json.loads((Path(__file__).resolve().parents[1] / 'fixtures/ce2_ce5_casos_corregidos.json').read_text(encoding='utf-8'))
CORE = [c for c in DATA['cases'] if c['id'] != 'C2_combined_defects']
EXTRA = [c for c in DATA['cases'] if c['id'] == 'C2_combined_defects']


def test_16_casos_cuatro_indicadores_y_extra_conservado():
    assert len(CORE) == 16
    assert len(EXTRA) == 1
    assert len(DATA['cases']) == 17
    assert len({c['id'] for c in DATA['cases']}) == 17
    for ind in ('CE2', 'CE3', 'CE4', 'CE5'):
        assert sorted(c['proposed_score'] for c in CORE if c['indicator'] == ind) == [0, 1, 2, 3]
    assert EXTRA[0]['indicator'] == 'CE2'
    assert EXTRA[0]['proposed_score'] is None


def test_estimulos_completos():
    for c in DATA['cases']:
        assert c['user_message'].strip() and c['assistant_response'].strip()
        assert '...' not in c['assistant_response']
        assert not c['expert_approved']


def test_controles_aplicabilidad_y_jerga():
    assert {c['id'] for c in DATA['additional_cases']} == {'C4_NA', 'C5_EXPLAINED'}


def test_no_oraculos_prematuros():
    assert all(c['adjudicated_score'] is None for c in DATA['cases'])
