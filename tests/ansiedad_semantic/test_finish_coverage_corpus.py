from backend.evaluators.ansiedad_semantic.finish_coverage_corpus import build
from backend.evaluators.ansiedad_semantic.technical_validation import prepare
from backend.evaluators.nd.docx_components import contracts

def test_missing_level_cases_keep_official_basis_and_disjoint_originals():
    rows=build()
    assert len({r['original']['input_sha256'] for r in rows})==len(rows)
    for row in rows:
        code=row['codes'][0];level=row['expected'][code]
        assert row['basis'][code]==contracts()[code]['levels'][str(level)]
        assert level in (0,1,2)

def test_middle_level_hypotheses_cover_all_missing_codes_without_af4_repeat():
    rows=build()
    actual={(r['codes'][0],r['expected'][r['codes'][0]]) for r in rows}
    assert {(code,level) for code in contracts() if code!='AF4' for level in (1,2)}<=actual
    assert not any(code=='AF4' for code,_ in actual)

def test_coverage_requests_do_not_leak_expectations():
    for row in build():
        for packet in prepare(row):
            assert not ({'expected','basis','split','before'} & packet.keys())
            assert packet['original']==row['original']

def test_ce10_preserves_own_prior_context():
    for row in build():
        if row['codes']==['CE10']:
            assert row['original']['turn']==2
            assert len(row['original']['prior_history'])==2
            assert row['original']['prior_history'][0]['role']=='user'
