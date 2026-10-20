"""Immutable, curated results archive. Never exposes source databases or receipts."""
from copy import deepcopy
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
import re
from zipfile import ZipFile

FORMAT='evalia-published-results-v1'
MAX_MEMBER=25_000_000
MAX_ARCHIVE=100_000_000

def clean_presentation(value):
    """Remove internal artifacts and reviewer metadata from public presentation."""
    private={'validated_audit','indicator_results','manual_evaluator','manual_created','receipt_path',
        'proposal','original_evidence','runtime_sources','source_signature','physical_signature',
        'execution_adapter','batch_evidence','sync_evidence','evidence'}
    if isinstance(value,dict):return {k:clean_presentation(v) for k,v in value.items() if k not in private}
    if isinstance(value,list):return [clean_presentation(v) for v in value]
    return value

class PublishedResults:
    def __init__(self,path,expected_hash):
        self.path=Path(path)
        if not re.fullmatch(r'[a-f0-9]{64}',expected_hash or ''):raise ValueError('Falta SHA-256 del archivo de resultados')
        if self.path.stat().st_size>MAX_ARCHIVE:raise ValueError('Archivo de resultados demasiado grande')
        if sha256(self.path.read_bytes()).hexdigest()!=expected_hash:raise ValueError('SHA-256 de resultados incorrecto')
        self.archive=ZipFile(self.path)
        try:
            names=self.archive.namelist()
            if len(names)!=len(set(names)) or len(names)>205:raise ValueError('Inventario de archivo invalido')
            if any(i.file_size>MAX_MEMBER for i in self.archive.infolist()):raise ValueError('Miembro de archivo demasiado grande')
            if sum(i.file_size for i in self.archive.infolist())>250_000_000:raise ValueError('Archivo expandido demasiado grande')
            self.manifest=self._read('manifest.json')
            if self.manifest.get('format')!=FORMAT:raise ValueError('Formato de resultados no reconocido')
            entries=self.manifest['experiments']
            self.experiment_ids=frozenset(e['id'] for e in entries)
            self.response_ids=frozenset(self.manifest['response_ids'])
            if any(type(i)is not int or i<=0 for i in (*self.experiment_ids,*self.response_ids)):raise ValueError('Identificadores invalidos')
            if len(self.experiment_ids)!=len(entries):raise ValueError('Experimentos duplicados')
            expected={'manifest.json','global.json',*[f'experiments/{i}.json' for i in self.experiment_ids]}
            if self.manifest.get('runtime_certificate'):
                expected.add('runtime/certificates.json')
            for asset in self.manifest.get('runtime_assets',[]):
                relative=asset['path']
                parts=relative.split('/')
                permitted=relative.startswith('docs/ansiedad_semantic/closure6_20261013/integral_live/ratification_06/') or (
                    relative.startswith('backend/evaluators/') and any(p in ('reports','backups') for p in parts))
                if not permitted or any(p in ('','..','.') for p in parts) or '\\' in relative or ':' in relative:
                    raise ValueError('Ubicacion de evidencia no autorizada')
                if asset['member']!='runtime/assets/'+relative:raise ValueError('Miembro de evidencia no valido')
                expected.add(asset['member'])
            if set(names)!=expected:raise ValueError('Archivos no autorizados en el paquete')
            for name,digest in self.manifest['members'].items():
                if name not in expected or sha256(self.archive.read(name)).hexdigest()!=digest:raise ValueError('Contenido no integro')
            if set(self.manifest['members'])!=expected-{'manifest.json'}:raise ValueError('Faltan huellas de contenido')
        except BaseException:
            self.archive.close();raise

    def _read(self,name):return json.loads(self.archive.read(name))

    def catalog(self):
        from backend.global_results import GROUPS
        return dict(experiments=deepcopy(self.manifest['experiments']),excluded_count=self.manifest.get('excluded_count',0),
            bank=self.manifest['bank'],groups=[dict(id=k,title=t,url=f'/resultados-globales?grupo={k}') for k,t,_ in GROUPS])

    @lru_cache(maxsize=2)
    def experiment(self,experiment_id):
        if experiment_id not in self.experiment_ids:raise KeyError(experiment_id)
        value=self._read(f'experiments/{experiment_id}.json')
        if value['details']['id']!=experiment_id or value['results']['experiment']['id']!=experiment_id:raise ValueError('Identidad de experimento incorrecta')
        return value

    @lru_cache(maxsize=1)
    def global_results(self):return self._read('global.json')

    def certificate_bytes(self):
        return self.archive.read('runtime/certificates.json') if self.manifest.get('runtime_certificate') else None

    def install_runtime_assets(self,root):
        root=Path(root).resolve()
        for asset in self.manifest.get('runtime_assets',[]):
            target=(root/asset['path']).resolve()
            if not target.is_relative_to(root):raise ValueError('Evidencia fuera del despliegue')
            raw=self.archive.read(asset['member'])
            if target.exists():
                if target.read_bytes()!=raw:raise ValueError('La evidencia de integridad difiere del archivo existente')
            else:
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
