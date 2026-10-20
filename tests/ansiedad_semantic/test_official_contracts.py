from pathlib import Path
from backend.evaluators.ansiedad_semantic.official_contracts import read_contracts, EXPECTED


def test_all_81_official_contracts_have_four_literal_levels_and_gate():
    root = Path(__file__).resolve().parents[2]
    result = read_contracts(root / 'PUNTAJES EVALUADORES ANSIEDAD(20261008-000023).docx')
    assert len(result['contracts']) == sum(EXPECTED.values()) == 81
    assert result['source_sha256'] == 'ac24c12bcc048c53d2749927ce7d19776ba7ecfa2d45441a90f81d7251e5439c'
    for item in result['contracts'].values():
        assert set(item['levels']) == {'0', '1', '2', '3'}
        assert all(text in item['paragraphs_literal'] for text in item['levels'].values())
        assert item['applicability_literal'] in item['paragraphs_literal']
