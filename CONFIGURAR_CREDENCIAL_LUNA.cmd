@echo off
cd /d "%~dp0"
if exist "docs\integration_controlled_20261014\runtime\python\cpython-3.11.15-windows-x86_64-none\python.exe" (
    set "PYTHONPATH=venv/Lib/site-packages;."
    "docs\integration_controlled_20261014\runtime\python\cpython-3.11.15-windows-x86_64-none\python.exe" -m backend.luna_credentials
) else if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m backend.luna_credentials
) else (
    python -m backend.luna_credentials
)
pause
