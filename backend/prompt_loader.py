import json
import hashlib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = BASE_DIR / "database" / "prompts"
BANKS_DIR = BASE_DIR / "database" / "scenario_banks"


def load_official_prompt(scenario_code: str):
    """Verified active bank, separate from immutable historical prompt files."""
    active = BANKS_DIR / "ACTIVE.json"
    if not active.exists():
        return None
    pointer = json.loads(active.read_text(encoding="utf-8"))
    version = pointer["version"]
    if Path(version).name != version:
        raise ValueError("Invalid bank version")
    folder = BANKS_DIR / version
    manifest_bytes = (folder / "MANIFEST.json").read_bytes()
    if hashlib.sha256(manifest_bytes).hexdigest() != pointer["manifest_sha256"]:
        raise ValueError("Official bank manifest hash mismatch")
    manifest = json.loads(manifest_bytes)
    name = f"{scenario_code}.json"
    if name not in manifest["files"]:
        return None
    raw = (folder / name).read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest["files"][name]:
        raise ValueError("Official scenario hash mismatch")
    prompt = json.loads(raw)
    if prompt.get("bank_version") != version or prompt.get("source_sha256") != manifest["source_sha256"]:
        raise ValueError("Official scenario provenance mismatch")
    return prompt


def load_prompt(scenario_code: str):
    official = load_official_prompt(scenario_code)
    if official is not None:
        return official
    file_path = PROMPTS_DIR / f"{scenario_code}.json"

    if not file_path.exists():
        return None

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)
