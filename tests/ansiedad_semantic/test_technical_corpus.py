"""Pre-registration boundaries: expected scores never reach semantic readers."""
import json
from backend.evaluators.ansiedad_semantic.technical_corpus import cases
from backend.evaluators.ansiedad_semantic.technical_validation import prepare
from backend.evaluators.nd.docx_components import contracts

def test_all_official_codes_and_disjoint_originals():
    corpus=cases()
    assert {c for row in corpus for c in row['codes']}==set(contracts())
    hashes=[row['original']['input_sha256'] for row in corpus]
    assert len(hashes)==len(set(hashes))
    assert {row['split'] for row in corpus}=={'development','heldout'}

def test_reader_packets_do_not_contain_expectations_or_other_originals():
    for case in cases():
        for packet in prepare(case):
            assert packet['original']==case['original']
            assert not ({'expected','basis','split','decisions'} & packet.keys())
            assert set(packet['indicators'])<=set(case['codes'])
            assert all('score' not in atom for atom in packet['indicators'].values())

def test_independent_verifier_has_no_extractor_output():
    for case in cases():
        packets=prepare(case)
        if packets:
            assert len(packets)==2
            assert packets[0]['stage']=='extract'
            assert packets[1]['stage']=='independent_verify'
            assert packets[0]['original']==packets[1]['original']
            assert 'extraction' not in packets[1]

def test_longitudinal_case_contains_only_preceding_own_turn():
    case=next(row for row in cases() if row['id']=='CE-full')
    original=case['original']
    assert original['turn']==2
    assert len(original['prior_history'])==2
    assert original['prior_history'][0]['role']=='user'
    assert original['prior_history'][1]['role']=='assistant'
    assert original['response'] not in json.dumps(original['prior_history'],ensure_ascii=False)
