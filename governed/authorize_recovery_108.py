"""Record the explicit 494-call / USD6 individual / USD7 global user approval."""
import asyncio,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'governed'),str(ROOT/'venv/Lib/site-packages')]
from deploy_bootstrap import create_app
from direct_recovery import digest,wire
async def main():
 cfg=json.loads((ROOT/'.evalia-private/governed_joint_install_20261017/config.json').read_text(encoding='utf8'));cfg['config_path']=str(ROOT/'.evalia-private/governed_joint_install_20261017/config.json')
 app=create_app(cfg);folder=ROOT/'.evalia-private/direct_recovery/108';m=json.loads((folder/'manifest.json').read_text(encoding='utf8'))
 ready=json.loads((folder/'READY.json').read_text(encoding='utf8'));assert ready['new_calls_required']==494 and ready['max_preventive_usd']=='2.75269825'
 class Request:
  headers={}
  async def json(self):return dict(confirmation='AUTORIZO',campaign=digest(m),individual_cap_usd='6.00',global_cap_usd='7.00')
 endpoint=next(r.endpoint for r in app.routes if r.path=='/api/experiments/{experiment}/direct-recovery/confirm')
 result=await endpoint(108,Request());(folder/'USER_APPROVED_LAUNCH.json').write_text(wire(result),encoding='utf8');print(wire(result))
if __name__=='__main__':asyncio.run(main())
