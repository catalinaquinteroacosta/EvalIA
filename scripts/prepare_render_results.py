"""Prepare a private deployment archive; never uploads or adds data to Git."""
import argparse
from collections import defaultdict
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import sys
from zipfile import ZipFile,ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.published_results import FORMAT,PublishedResults,clean_presentation

def encode(value):return json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()

def runtime_assets(root):
    """Keep the original integrity manifest and the evidence it actually hashes."""
    import subprocess,re
    root=Path(root)
    tracked=set(subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0'))
    folder=root/'docs/ansiedad_semantic/closure6_20261013/integral_live/ratification_06'
    required={str((folder/name).relative_to(root)).replace('\\','/') for name in ('FREEZE.json','code_manifest.json','files.json')}
    for name in ('code_manifest.json','files.json'):
        for entry in json.loads((folder/name).read_text(encoding='utf8')):
            relative=entry['path'].replace('\\','/')
            path=root/relative
            if sha256(path.read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('Dependencia congelada modificada: '+relative)
            if relative not in tracked:required.add(relative)
    members={};assets=[]
    for relative in sorted(required):
        raw=(root/relative).read_bytes()
        if re.search(rb'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{32,}',raw):raise ValueError('Posible credencial en evidencia; no se incluye')
        member='runtime/assets/'+relative;members[member]=raw;assets.append(dict(path=relative,member=member))
    return members,assets

def prepare(config_path,output):
    from backend.global_results import classified_report,report
    from governed.direct_recovery import consolidated
    from governed.direct_presentation import present
    from types import SimpleNamespace
    config=json.loads(Path(config_path).read_text(encoding='utf8'))
    manual=Path(config['project_root'])/'.evalia-private/direct_recovery/recovery.db'
    def connect():
        db=sqlite3.connect(Path(config['database']).resolve().as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row;return db
    stub=SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(direct_recovery_config=config,direct_recovery_database=manual)),get_connection=connect)
    global_data=classified_report(report(stub))
    if len(global_data['experiments'])!=38 or sum(r['pending'] for r in global_data['responses']):raise ValueError('Se requieren los 38 escenarios oficiales completos')
    members={'global.json':encode(clean_presentation(global_data))};response_ids=[];numeric=na=0
    for experiment in global_data['experiments']:
        eid=experiment['id'];print(f'Preparando {experiment["code"]} · experimento {eid}',flush=True)
        with connect() as db:
            scenario=dict(db.execute('SELECT s.* FROM scenarios s JOIN experiments e ON e.scenario_id=s.id WHERE e.id=?',(eid,)).fetchone())
            raw=[dict(r) for r in db.execute('''SELECT r.id AS response_id,t.id AS turn_id,t.turn_number,t.user_message,
                r.response_text,m.id AS model_id,m.name AS model_name,m.provider FROM responses r
                JOIN conversation_turns t ON t.id=r.turn_id JOIN ai_models m ON m.id=r.ai_model_id
                WHERE r.experiment_id=? ORDER BY t.turn_number,m.name''',(eid,))]
        experiment.update(status='evaluated',rubric_type=scenario['rubric_type'])
        data=consolidated(config,eid,manual)
        if len(raw)!=25 or not data['complete']:raise ValueError('Experimento incompleto')
        numeric+=data['summary']['numeric'];na+=data['summary']['states'].get('N/A',0)
        models={r['model_name']:dict(id=r['model_id'],name=r['model_name'],provider=r['provider']) for r in raw}
        results=[dict(response_id=r['response_id'],turn_number=r['turn_number'],user_message=r['user_message'],response_text=r['response_text'],
            model=models[r['model_name']],evaluated=False,evaluation=None) for r in raw]
        payload=dict(experiment=dict(id=eid,status='evaluated',scenario_code=scenario['code'],scenario_title=scenario['title'],rubric_type=scenario['rubric_type']),
            summary=dict(responses_saved=25),results=results,conversation_results=[],models=list(models.values()))
        public=clean_presentation(present(payload,data))
        turns={r['turn_number']:dict(id=r['turn_id'],turn_number=r['turn_number'],user_message=r['user_message']) for r in raw}
        details=dict(id=eid,status='evaluated',created_at=None,updated_at=None,historical_read_only=True,
            scenario={**{k:scenario[k] for k in ('id','code','category','title','description','rubric_type')},'turns':list(turns.values())},models=list(models.values()))
        members[f'experiments/{eid}.json']=encode(dict(details=details,results=public))
        response_ids.extend(r['response_id'] for r in raw)
    # This server-only certificate metadata is not exposed through public APIs.
    certificate=ROOT/'docs/economic_readers_step3_2_20261016/adjudicated_final_20261016/qualification_v19/CERTIFICATES_COMPATIBLE_V7.json'
    if certificate.is_file():members['runtime/certificates.json']=certificate.read_bytes()
    assets,asset_manifest=runtime_assets(ROOT);members.update(assets)
    manifest=dict(format=FORMAT,created_at=datetime.now(timezone.utc).isoformat(),bank=global_data['bank'],dataset_id=global_data['dataset_id'],
        experiments=global_data['experiments'],response_ids=response_ids,excluded_count=len(global_data['excluded']),
        numeric=numeric,na=na,runtime_certificate=certificate.is_file(),runtime_assets=asset_manifest,members={k:sha256(v).hexdigest() for k,v in members.items()})
    output=Path(output).resolve()
    if output==Path(config['database']).resolve() or output.suffix!='.zip':raise ValueError('El destino debe ser un ZIP separado')
    output.parent.mkdir(parents=True,exist_ok=True);temporary=output.with_suffix('.tmp')
    with ZipFile(temporary,'w',compression=ZIP_DEFLATED,compresslevel=9) as archive:
        for name,value in members.items():archive.writestr(name,value)
        archive.writestr('manifest.json',encode(manifest))
    digest=sha256(temporary.read_bytes()).hexdigest()
    check=PublishedResults(temporary,digest);check.archive.close();temporary.replace(output)
    receipt=dict(file=output.name,sha256=digest,bytes=output.stat().st_size,experiments=len(manifest['experiments']),responses=len(response_ids),numeric=numeric,na=na,
        distribution='Private deployment asset; do not commit to the source repository',
        contains=['simulated conversations','persisted grades and justifications','public comparison tables','server-only qualification certificate metadata','original hashed runtime integrity evidence'],
        excludes=['API credentials','billing ledgers','raw research databases','raw API receipts','reviewer metadata'])
    output.with_suffix('.manifest.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(receipt,ensure_ascii=False,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);parser.add_argument('--output',default=str(ROOT/'exports/render/EvalIA_resultados.zip'))
    args=parser.parse_args();prepare(args.config,args.output)
