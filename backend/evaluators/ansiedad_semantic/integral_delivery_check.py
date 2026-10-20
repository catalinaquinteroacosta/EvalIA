"""Read-only evidence checks, with a new append-only check artifact."""
import json
from pathlib import Path
from hashlib import sha256
from .integral_checkpoint import read, save
from .closure_integral_live import LIVE
from backend.evaluators.nd.contracts import Evidence, TurnContext, HistoryTurn

def run():
    final=LIVE/'final_01';out=LIVE/'delivery_checks_02';out.mkdir(exist_ok=False)
    records=read(final/'accepted_critical_results.json')
    records += [{'code':c,**d} for c,d in read(final/'integration_new_verified_results.json').items()]
    citations=0;errors=[];sources=[]
    for rec in records:
        p=Path(rec['source']);base=p.parent
        original_source=base/'extract.json'
        if not original_source.exists():original_source=base/'independent_verify.json'
        d=read(original_source);o=d['request']['original']
        ctx=TurnContext(o['user'],o['response'],tuple(HistoryTurn(**h) for h in o['prior_history']))
        r=rec['result'];sources.append({'code':rec['code'],'original_source':str(original_source),
            'input_sha256':o['input_sha256'],'result_source':str(p)})
        if 'reviews' in r:
            roles={'combined_verified_reviews':{x['name']:x for x in r['reviews']}}
        else:
            roles={role:r[role]['components'] for role in ['extraction',('verification' if 'verification' in r else 'independent_verification')]}
        for role,components in roles.items():
            for name,component in components.items():
                if component['complete_response_reviewed'] is not True:errors.append([rec['code'],role,name,'incomplete review'])
                for e in component['evidence']+component['counterevidence']:
                    citations+=1
                    if not Evidence(**e).verify_exact(ctx):errors.append([rec['code'],role,name,'nonliteral or forbidden history',e])
    check={'accepted_case_results_checked':len(records),'literal_references_checked_including_duplicates':citations,
        'errors':errors,'all_current_local_tests_passed':read(LIVE/'local_final_01/command.json')['exit_code']==0,
        'sources':sources,'meaning_review_not_replaced_by_literal_audit':True}
    assert not errors and check['all_current_local_tests_passed']
    save(out/'evidence_checks.json',check)
    paths=[Path('backend/evaluators/ansiedad_semantic')/n for n in ['functional_review.py','guardrail_review.py','gd_component_review.py','closure_integral_live.py','cash_safe_transport.py','integral_checkpoint.py','integral_delivery_check.py']]
    paths += list(Path('tests/ansiedad_semantic').glob('test_*adjudication.py'))
    paths += [Path('tests/ansiedad_semantic')/n for n in ['test_integral_contradiction_guards.py','test_cash_safe_transport.py','test_gd7_conjunction_revision.py']]
    save(out/'code_hashes.json',[{'path':str(p),'sha256':sha256(p.read_bytes()).hexdigest()} for p in paths])
    save(out/'files.json',[{'path':str(p),'sha256':sha256(p.read_bytes()).hexdigest()} for p in out.iterdir() if p.is_file()])
    print(json.dumps({k:v for k,v in check.items() if k!='sources'}))

if __name__=='__main__':run()
