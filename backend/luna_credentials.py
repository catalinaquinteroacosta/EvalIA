"""Windows user-bound encrypted credential; never returned by HTTP."""
import os
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FILE=ROOT/'.evalia-private/luna_api_key.dpapi'

def available():return bool(os.environ.get('OPENAI_API_KEY')) or FILE.is_file()

def _powershell(script, data):
    result=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',script],input=data,
                          capture_output=True,text=True,timeout=20)
    if result.returncode:raise RuntimeError('No se pudo acceder a la credencial cifrada de Windows.')
    return result.stdout.strip()

def preserve_environment_key(replace=False):
    if FILE.exists() and not replace:return 'existing_encrypted_credential_preserved'
    key=os.environ.get('OPENAI_API_KEY')
    if not key:return 'credential_not_available'
    encoded=_powershell("Add-Type -AssemblyName System.Security; $s=[Console]::In.ReadToEnd(); [Convert]::ToBase64String([Security.Cryptography.ProtectedData]::Protect([Text.Encoding]::UTF8.GetBytes($s),$null,[Security.Cryptography.DataProtectionScope]::CurrentUser))",key)
    FILE.parent.mkdir(exist_ok=True)
    if FILE.exists():
        from datetime import datetime
        backup=FILE.with_name(FILE.name+'.'+datetime.now().strftime('%Y%m%d%H%M%S')+'.backup')
        backup.write_bytes(FILE.read_bytes())
        FILE.write_text(encoded,encoding='ascii')
    else:
        with FILE.open('x',encoding='ascii') as f:f.write(encoded)
    return 'credential_encrypted_for_current_windows_user'

def load():
    if os.environ.get('OPENAI_API_KEY') and not (FILE.is_file() and os.environ.get('EVALIA_LUNA_USE_PROTECTED_KEY')=='1'):return True
    if not FILE.is_file():return False
    key=_powershell("Add-Type -AssemblyName System.Security; $s=[Console]::In.ReadToEnd(); [Text.Encoding]::UTF8.GetString([Security.Cryptography.ProtectedData]::Unprotect([Convert]::FromBase64String($s),$null,[Security.Cryptography.DataProtectionScope]::CurrentUser))",FILE.read_text(encoding='ascii'))
    if not key:raise RuntimeError('Credencial cifrada vacía.')
    os.environ['OPENAI_API_KEY']=key
    return True

if __name__=='__main__':
    import getpass
    replace=FILE.exists()
    if replace and input('Existe una credencial cifrada. Escribe REEMPLAZAR para actualizarla conservando copia cifrada: ')!='REEMPLAZAR':raise SystemExit('Credencial existente conservada.')
    key=getpass.getpass('Clave OpenAI para el lector Luna (entrada oculta): ')
    if not key.strip():raise SystemExit('No se guardó una clave vacía.')
    os.environ['OPENAI_API_KEY']=key.strip()
    preserve_environment_key(replace=replace)
    print('Credencial protegida para este usuario de Windows. No se hizo ninguna llamada API.')
