import importlib.util,json
from pathlib import Path
from backend import luna_reader as current

def before():
    p=Path('docs/economic_readers_step3_20261015/corrections_02/luna_reader_before_r3.py')
    s=importlib.util.spec_from_file_location('luna_before_relational',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def test_only_confirmed_relational_scopes_change_effective_requests():
    old=before();templates=json.loads(Path('docs/economic_readers_step1_20261015/BASE_TEMPLATES_NOT_SENT.json').read_text(encoding='utf8'))
    changed={'CR-OP4','CR-RI2','CR-CS1','CR-CS8','CR-OP2','CR-OP5','EM9','ND8','CR-CE6','CR-CE7','CR-GA2','CR-GA3','CR-GA6','CR-GA7','CR-GA9','CR-OP6','CR-CS7','CR-CS10','CR-CS11','CR-RI1','CR-CT1','AF6','PS9','PS1','PS5','CE8','PA6','PA7','CP2','GD5','IR8','CR-RE4'};same=0;different=0
    changed.update('EM7 EM10 CP3 CP5 IR4 IR5 IR6 ND2 PA2 PA3 PA4 PA8 AF2 AF3 AF7 AF8 CE1 CE2 CE3 CE4 CE9 GD1 GD3 GD4 GD8 CR-CS3 CR-NI4 CR-PP1 CR-PP8 CR-PP9 CR-AC4 CR-RE3 CR-RE6 CR-RE8 CR-RE9 CR-CE4 CR-CE9 CR-RI5'.split())
    changed.update('CR-OP1 CR-OP3 CR-OP10 CR-NI7 CR-RE1 CR-CE3 CR-AC6'.split())
    changed.update('ND7 CR-NI9 CR-CT10 CR-PP5 CR-RE7'.split())
    for t in templates:
        a=old.adapt_body(t['body'],t['endpoint']);b=current.adapt_body(t['body'],t['endpoint'])
        payload=json.loads(t['body'].get('input',t['body'].get('messages'))[1]['content'])
        codes={d['code'] for d in payload['predicates'].values()} if 'predicates' in payload else set(payload['indicators'])
        if not codes & changed:assert a==b;same+=1
        else:
            # Own-scope refinements deliberately leave mixed family bodies
            # identical when that refinement is not applicable to the body.
            if a==b:same+=1;continue
            different+=1
            old_payload=json.loads(a.get('input',a.get('messages'))[1]['content'])
            new_payload=json.loads(b.get('input',b.get('messages'))[1]['content'])
            # Scoped reasoning and reported evidence may change; the official
            # predicates/components and original texts must remain identical.
            for key in ('predicates','indicators','conversation','original'):
                if key in old_payload:assert old_payload[key]==new_payload[key]
            if 'response_format' in a:assert a['response_format']==b['response_format']
            if 'text' in a:assert a['text']==b['text']
    assert same>0 and different>0

def test_relational_prompt_requires_referents_without_scoring_or_overrides():
    for code in current._RELATIONAL_READING:
        assert '?' not in current._RELATIONAL_READING[code]
    assert current.effective_clarifications(['CR-CE10'])==before().effective_clarifications(['CR-CE10'])
    assert current.effective_clarifications(['AF1','CR-CT3'])==before().effective_clarifications(['AF1','CR-CT3'])
    assert current.VERSION.endswith('-19')
