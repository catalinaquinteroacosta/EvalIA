"""Joint offline verification; capture native exit codes and UTF-8 logs."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from crisis_semantic.domain import DOCS
from crisis_semantic.span_provider import fingerprint

def main(closure=False,only_python=False):
    root = Path(__file__).resolve().parents[3]
    folder = DOCS / "closure8" if closure else DOCS / "step8" / fingerprint()[:12]
    folder.mkdir(parents=True, exist_ok=True)
    commands = {
        "python_tests": [sys.executable,"-B","-m","unittest","discover","-s","tests/crisis_semantic","-p","test_*.py","-v"],
        "node_tests": ["node","--test","--test-reporter=tap","tests/crisis_semantic/contracts.test.mjs"],
        "documentary_validation": ["node","backend/evaluators/crisis_semantic/validate_contracts.mjs"],
    }
    if only_python:commands={name:command for name,command in commands.items() if name=='python_tests'}
    def check(item):
        name,command = item
        result = subprocess.run(command,cwd=root,capture_output=True,encoding="utf-8",errors="replace")
        log = folder / (name + ".txt")
        log.write_text(result.stdout + result.stderr,encoding="utf-8")
        return name, {"command":command,"exit_code":result.returncode,"log":str(log.relative_to(root)),"sha256":hashlib.sha256(log.read_bytes()).hexdigest()}
    with ThreadPoolExecutor(max_workers=3) as pool:
        new_results = dict(pool.map(check,commands.items()))
    previous=folder/'verification.json'
    results=json.loads(previous.read_text(encoding='utf-8')) if only_python and previous.exists() else {}
    results.update(new_results)
    (folder / "verification.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
    print(json.dumps(results,indent=2))
    return int(any(r["exit_code"] for r in results.values()))

if __name__ == "__main__":
    sys.exit(main('--closure' in sys.argv,'--python-only' in sys.argv))
