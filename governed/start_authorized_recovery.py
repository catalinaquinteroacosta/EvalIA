"""Explicitly start only an existing experiment's standing authorized fallback."""
import sys,json,argparse
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root),str(root/'governed'),str(root/'venv/Lib/site-packages')]
from automatic_direct_recovery import start
p=argparse.ArgumentParser();p.add_argument('experiment',type=int);a=p.parse_args()
cfg=json.loads((root/'.evalia-private/governed_joint_install_20261017/config.json').read_text())
start(cfg,a.experiment)
print('Authorized recovery launched for experiment',a.experiment)
