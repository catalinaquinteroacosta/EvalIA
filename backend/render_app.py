"""Render factory: immutable published research and a separate temporary workbench."""
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit
from fastapi.responses import JSONResponse
from backend.published_results import PublishedResults,MAX_ARCHIVE

ROOT=Path(__file__).resolve().parents[1]

def download_archive(url,target,expected_hash,token=None):
    import requests
    parsed=urlsplit(url)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('La descarga de resultados requiere una URL HTTPS')
    headers={}
    if parsed.hostname=='api.github.com':
        headers['Accept']='application/octet-stream'
        if token:headers['Authorization']='Bearer '+token
    elif token:
        raise ValueError('El token de GitHub solo se envia a api.github.com')
    if parsed.hostname=='api.github.com' and '/releases/tags/' in parsed.path:
        with requests.get(url,headers=dict(headers,Accept='application/vnd.github+json'),timeout=(15,30)) as response:
            response.raise_for_status();metadata=response.json()
        assets=[a for a in metadata.get('assets',[]) if a.get('name')=='EvalIA_resultados.zip']
        if len(assets)!=1:raise ValueError('La publicacion debe contener un unico EvalIA_resultados.zip')
        asset_url=assets[0]['url'];asset=urlsplit(asset_url)
        if asset.scheme!='https' or asset.hostname!='api.github.com' or not re.fullmatch(r'/repos/[^/]+/[^/]+/releases/assets/\d+',asset.path):
            raise ValueError('Enlace de archivo de GitHub no valido')
        return download_archive(asset_url,target,expected_hash,token)
    target.parent.mkdir(parents=True,exist_ok=True)
    temporary=target.with_suffix('.download')
    try:
        with requests.get(url,headers=headers,stream=True,timeout=(15,120)) as response:
            response.raise_for_status()
            if urlsplit(response.url).scheme!='https':raise ValueError('Redireccion de descarga insegura')
            size=0
            with temporary.open('wb') as output:
                for chunk in response.iter_content(1024*256):
                    size+=len(chunk)
                    if size>MAX_ARCHIVE:raise ValueError('Descarga demasiado grande')
                    output.write(chunk)
        # Validate before replacing an existing approved snapshot.
        checked=PublishedResults(temporary,expected_hash);checked.archive.close()
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)

def create_app():
    work=Path(os.environ.get('EVALIA_WORK_DIR',ROOT/'.evalia-private/render_work')).resolve()
    if work in {ROOT,ROOT/'.evalia-private/luna_ui',ROOT/'database'}:
        raise ValueError('El despliegue requiere una base temporal separada')
    work.mkdir(parents=True,exist_ok=True)
    digest=os.environ.get('EVALIA_RESULTS_SHA256','')
    source=os.environ.get('EVALIA_RESULTS_FILE')
    if source:
        archive_path=Path(source).resolve()
    else:
        url=os.environ.get('EVALIA_RESULTS_URL')
        if not url:raise RuntimeError('Falta configurar el archivo de resultados originales; no se publica una instalacion vacia')
        archive_path=work/'published-results.zip'
        download_archive(url,archive_path,digest,os.environ.get('EVALIA_RESULTS_TOKEN'))
    archive=PublishedResults(archive_path,digest)
    archive.install_runtime_assets(ROOT)
    # This factory is a dedicated process. Its original research databases are
    # never opened; only the empty temporary workbench accepts new experiments.
    os.environ['EVALIA_CLOUD_RUNTIME_ROOT']=str(work/'service')
    from run_evalia import base_app
    app=base_app(work/'workbench.db')
    app.state.published_results=archive
    app.state.public_origin=(os.environ.get('RENDER_EXTERNAL_URL') or os.environ.get('EVALIA_PUBLIC_ORIGIN','')).rstrip('/') or None
    app.state.temporary_experiments=True
    from backend import database,luna_real_ui
    certificate=archive.certificate_bytes()
    if certificate:
        path=work/'certificates.json';path.write_bytes(certificate)
        luna_real_ui.CERTIFICATES=path
    with database.get_connection() as db:
        for table,floor in [('experiments',max(archive.experiment_ids,default=0)+10000),
                            ('responses',max(archive.response_ids,default=0)+100000)]:
            row=db.execute('SELECT seq FROM sqlite_sequence WHERE name=?',(table,)).fetchone()
            if row:db.execute('UPDATE sqlite_sequence SET seq=max(seq,?) WHERE name=?',(floor,table))
            else:db.execute('INSERT INTO sqlite_sequence(name,seq) VALUES(?,?)',(table,floor))

    @app.middleware('http')
    async def protect_research(request,call_next):
        if request.method not in ('GET','HEAD','OPTIONS'):
            match=re.match(r'^/api/(experiments|responses)/(\d+)(?:/|$)',request.url.path)
            if match and int(match[2]) in (archive.experiment_ids if match[1]=='experiments' else archive.response_ids):
                return JSONResponse({'detail':'Las evaluaciones originales son de solo lectura. Crea un experimento nuevo.'},403)
            if request.headers.get('content-type','').startswith('application/json'):
                try:body=await request.json()
                except (ValueError,UnicodeError):body={}
                if isinstance(body,dict):
                    eid=body.get('experiment_id');rid=body.get('response_id')
                    protected=(type(eid)is int and eid in archive.experiment_ids) or (type(rid)is int and rid in archive.response_ids)
                    ids=body.get('response_ids',[])
                    if isinstance(ids,list):protected=protected or any(type(i)is int and i in archive.response_ids for i in ids)
                    if protected:return JSONResponse({'detail':'Las evaluaciones originales estan protegidas contra cambios.'},403)
        return await call_next(request)

    @app.get('/healthz')
    def health():return dict(status='ok',original_experiments=len(archive.experiment_ids),temporary_experiments=True)
    @app.get('/api/deployment')
    def deployment():return dict(mode='render_free',temporary_experiments=True,original_results_read_only=True,
        note='Los resultados originales se conservan. Los experimentos nuevos son temporales y pueden perderse al reiniciar; descarga los resultados que quieras conservar.')
    @app.get('/api/multi/status')
    def status():
        state=app.state.luna_real_service.status()
        return dict(state,jobs=[dict(id=p['id'],experiment=p['experiment_ids'][0]) for p in state['plans'] if p.get('experiment_ids')])
    return app
