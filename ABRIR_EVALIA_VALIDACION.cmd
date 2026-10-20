@echo off
cd /d "%~dp0"
set "PYTHONIOENCODING=utf-8"
set "EVALIA_LUNA_USE_PROTECTED_KEY=1"
if exist "docs\integration_controlled_20261014\runtime\python\cpython-3.11.15-windows-x86_64-none\python.exe" (
    set "PYTHONPATH=venv/Lib/site-packages;."
    "docs\integration_controlled_20261014\runtime\python\cpython-3.11.15-windows-x86_64-none\python.exe" -B run_evalia.py %*
) else if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -B run_evalia.py %*
) else if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" -B run_evalia.py %*
) else (
    python -B run_evalia.py %*
)
if errorlevel 1 pause
