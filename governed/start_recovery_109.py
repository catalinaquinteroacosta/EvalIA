"""Launch only the user's standing authorized #109 blocked-indicator recovery."""
import sys,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root),str(root/'governed'),str(root/'venv/Lib/site-packages')]
from automatic_direct_recovery import start
cfg=json.loads((root/'.evalia-private/governed_joint_install_20261017/config.json').read_text())
start(cfg,109)
print('Recovery 109 launch requested; no historical request repeated.')
