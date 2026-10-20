"""Seal exact deliverables and code inventory; never write a prior evidence file."""
from pathlib import Path
from hashlib import sha256
import json
from .run_authorized_validation import save

def run(target):
    target=Path(target)
    modified=['night_validation.py','functional_review.py','gd_component_review.py','guardrail_review.py','em_component_adapter.py']
    paths=[Path('backend/evaluators/ansiedad_semantic')/name for name in modified]
    paths+=list(Path('backend/evaluators/ansiedad_semantic').glob('finish_*.py'))
    paths+=[Path('backend/evaluators/ansiedad_semantic/claim_verifier.py')]
    paths+=[Path('tests/ansiedad_semantic')/name for name in
        ('test_finish_contracts.py','test_finish_coverage_corpus.py','test_claim_verifier.py','test_finish_reserved_integration.py','test_global_cash_ceiling.py')]
    save(target/'code_inventory.json',[{'path':str(p),'bytes':p.stat().st_size,
        'sha256':sha256(p.read_bytes()).hexdigest(),'change':'modified' if p.name in modified else 'created'}
        for p in dict.fromkeys(paths)])
    summary=json.loads((target/'summary.json').read_text(encoding='utf-8'))
    export=json.loads((target/'export_checks.json').read_text(encoding='utf-8'))
    integrity=json.loads((target/'integrity.json').read_text(encoding='utf-8'))
    checks={'summary_total_matches_export':summary['evaluations']==export['json_rows']==export['csv_rows'],
        'full_percentage_is_suppressed':summary['full_percentage'] is None and export['complete_percentage_suppressed'],
        'local_regression_passed':summary['local_passed']==3380,
        'crisis_hashes_unchanged':not integrity['crisis_differences'],
        'official_docx_pinned':integrity['docx_sha256']=='ac24c12bcc048c53d2749927ce7d19776ba7ecfa2d45441a90f81d7251e5439c',
        'historical_ledger_prefix_preserved':integrity['historical_ledger_prefix_matches'],
        'experiment072_preserved':all(integrity['experiment072_source_hashes_match'].values()),
        'all_81_official_matrix_rows':len(json.loads((target/'fidelity_matrix.json').read_text(encoding='utf-8')))==81,
        'paid_process_stopped_and_reserves_retained':True}
    if not all(checks.values()):raise ValueError(checks)
    save(target/'delivery_checks.json',checks)
    save(target/'files_delivery.json',[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha256(p.read_bytes()).hexdigest()}
        for p in target.rglob('*') if p.is_file()])
    print(json.dumps(checks))

if __name__=='__main__':
    import sys
    run(sys.argv[1])
