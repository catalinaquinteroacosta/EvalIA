"""Read-only checks of the files Git would publish. Never prints credentials."""
import ast
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def source_files():
    raw = subprocess.check_output(
        ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT)
    return sorted(set(p for p in raw.decode('utf8').split('\0') if p))


def main():
    problems = []
    files = source_files()
    secret = re.compile(rb'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{32,}')
    for name in files:
        path = ROOT / name
        if not path.is_file():
            continue
        parts = set(path.relative_to(ROOT).parts)
        if parts & {'.evalia-private', 'venv', '.venv', 'private_runtime', 'node_modules'}:
            problems.append((name, 'local/private directory'))
        if path.suffix.lower() in {'.db', '.sqlite', '.sqlite3', '.dpapi', '.pem', '.key'}:
            problems.append((name, 'database or credential'))
        if path.stat().st_size >= 50_000_000:
            problems.append((name, 'large generated file'))
            continue
        raw = path.read_bytes()
        if secret.search(raw):
            problems.append((name, 'possible API credential; inspect locally'))
        if path.suffix == '.py':
            try:
                ast.parse(raw, filename=name)
            except (SyntaxError, UnicodeError) as error:
                problems.append((name, f'invalid Python at line {getattr(error, "lineno", "?")}'))
    for name, reason in problems:
        print(f'{name}: {reason}')
    print(f'{len(files)} publication files checked; {len(problems)} problems.')
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
