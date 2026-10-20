"""Explicit offline installer. No restart, workers, authorization or API.
Requires closed server port, approved consistent-backup installation window.
Rollback restores code ONLY and never restores accounting/database files.
"""
import json,hashlib,shutil,sqlite3,socket
from pathlib import Path
def install(package,target,backup,db,*,installation_approved=False,quiescent_verified=False,server_port=8879):
    if installation_approved is not True or quiescent_verified is not True:raise ValueError('explicit approved quiescent installation required')
    with socket.socket() as sock:
        sock.settimeout(.3)
        if sock.connect_ex(('127.0.0.1',server_port))==0:raise ValueError('server still listening; installer never stops it')
    package=Path(package).resolve();target=Path(target).resolve();backup=Path(backup).resolve();db=Path(db).resolve()
    if backup.exists():raise ValueError('never overwrite backup')
    m=json.loads((package/'PACKAGE.json').read_text(encoding='utf8'));sources={}
    for name,digest in m['sha256'].items():
        p=(package/name).resolve()
        if not p.is_relative_to(package) or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise ValueError('candidate hash changed')
        sources[name]=p
    backup.mkdir(parents=True);s=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True);d=sqlite3.connect(backup/'application.db')
    try:s.backup(d);assert d.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    finally:s.close();d.close()
    history=[]
    for name,p in sources.items():
        destination=target/'governed'/name
        if name=='real_mode_governed.js':destination=target/'frontend/real_mode.js'
        rel=str(destination.relative_to(target));prior=backup/'code'/rel
        if destination.exists():prior.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(destination,prior)
        history.append(dict(path=rel,had_original=destination.exists(),installed_sha256=m['sha256'][name]))
        destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,destination)
    (backup/'INSTALL.json').write_text(json.dumps(dict(target=str(target),files=history,database_backup_not_for_rollback=True),indent=2),encoding='utf8')
    return history
def rollback_code(backup,*,workers_stopped=False):
    if workers_stopped is not True:raise ValueError('stop acquisition and drain/fence workers first')
    backup=Path(backup).resolve();m=json.loads((backup/'INSTALL.json').read_text(encoding='utf8'));target=Path(m['target']).resolve()
    # Never removes newly added code; preserves evidence and avoids recursive deletes.
    for row in m['files']:
        p=(target/row['path']).resolve()
        if not p.is_relative_to(target):raise ValueError('foreign rollback path')
        if hashlib.sha256(p.read_bytes()).hexdigest()!=row['installed_sha256']:raise ValueError('code changed after install; manual review required')
        if row['had_original']:shutil.copyfile(backup/'code'/row['path'],p)
    return 'Prior code restored; added modules retained inactive; databases/receipts/reserves untouched.'
