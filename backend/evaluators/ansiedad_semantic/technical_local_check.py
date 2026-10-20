"""Run the previously selected offline suite and retain exact command/output."""
from pathlib import Path
import json,subprocess
from .run_authorized_validation import save

def run(source,target):
    target=Path(target);target.mkdir(parents=True,exist_ok=False)
    command=json.loads(Path(source).read_text(encoding='utf-8'))['command']
    result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding='utf-8',errors='replace')
    with (target/'tests.txt').open('x',encoding='utf-8') as output:output.write(result.stdout)
    save(target/'command.json',{'command':command,'exit_code':result.returncode,'api_calls':0})
    print(result.stdout[-2200:]);print('exit_code',result.returncode)

if __name__=='__main__':
    import sys
    run(sys.argv[1],sys.argv[2])
