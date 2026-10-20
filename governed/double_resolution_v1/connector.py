"""Reuse durable native transport, but require a NEW subset campaign grant."""
import json,hashlib
from pathlib import Path
from sealed_governed_provider import SealedGovernedProvider
from .authorization import active
from .engine import digest
class CampaignProvider(SealedGovernedProvider):
    def __init__(self,lab,job,authorization_path,private_root,manifest):
        permission=active(lab,manifest)
        self.lab=lab;self.job=job;self.root=Path(private_root);self.prepared={}
        self.auth=json.loads(Path(authorization_path).read_text(encoding='utf8'))
        if self.auth.get('campaign_authorization_id')!=permission['authorization_id'] or self.auth.get('explicit_user_approval')is not True or self.auth.get('scope')!='double-resolution-exact-campaign':raise ValueError('historical grant cannot authorize adjudication')
        raw=Path(self.auth['manifest_path']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=self.auth['sealed_manifest_sha256']:raise ValueError('native manifest changed')
        self.manifest=json.loads(raw);self.requests={digest(r['body']):r for r in self.manifest['requests']}
        if set(self.requests)!={digest(r['body']) for r in manifest['requests']} or self.auth['allowed_experiment_ids']!=[manifest['cases'][0]['experiment']]:raise ValueError('campaign body scope differs')
        con=lab.connect()
        try:
            for key in self.requests:
                row=con.execute('SELECT job FROM requests WHERE key=?',(key,)).fetchone()
                if not row or row[0]!=job:raise ValueError('foreign coordinator request')
        finally:con.close()
