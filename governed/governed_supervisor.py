"""Explicit Windows worker supervisor. Import starts nothing and loads no key."""
import json,subprocess,threading,time
from pathlib import Path
from governed_parallel import GovernedLab
from supervision import Fence

class Supervisor:
    def __init__(self,config_path):
        self.path=Path(config_path).resolve();self.config=json.loads(self.path.read_text(encoding='utf8'));self.children=[];self.thread=None
        self.lab=GovernedLab(self.config['coordinator']);self.fence=Fence(Path(self.config['fences'])/'supervisor.lock');self.stop_requested=threading.Event()
    def start(self):
        p=self.lab.policy()
        if type(self.config.get('explicit_real_activation')) is not bool or p['mode']!='real' or not p['rpm'] or not p['tpm']:raise ValueError('verified policy required; paused supervision sends nothing')
        if not self.fence.acquire():raise ValueError('another supervisor owns this queue')
        self.thread=threading.Thread(target=self.watch,daemon=True);self.thread.start()
    def watch(self):
        try:
            while not self.stop_requested.is_set():
                self.config=json.loads(self.path.read_text(encoding='utf8'))
                self.children=[p for p in self.children if p.poll() is None]
                # Dispatch needs only queue state, not the full results/timing report.
                with self.lab.connect() as c:
                    state=dict(global_blocked=bool(c.execute('select blocked from safety').fetchone()[0]),workers=c.execute('select workers from settings').fetchone()[0],jobs=[dict(r)for r in c.execute('select status from jobs')])
                running=sum(j['status']=='running' for j in state['jobs'])
                if self.config.get('explicit_real_activation') is True and not state['global_blocked'] and any(j['status']=='queued' for j in state['jobs']):
                    for _ in range(max(0,state['workers']-max(len(self.children),running))):
                        flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
                        log=Path(self.config['fences']).parent/'authorized_workers.log'
                        with log.open('ab')as output:
                            self.children.append(subprocess.Popen([self.config['python'],'-X','utf8','-B',str(Path(__file__).with_name('official_queue_worker.py')),'--config',str(self.path)],cwd=self.config['project_root'],stdout=output,stderr=output,creationflags=flags))
                # No recovery/re-enqueue on timeout or exit. Interrupted jobs retain state.
                time.sleep(.5)
        finally:self.fence.release()
    def status(self):return dict(supervisor_alive=bool(self.thread and self.thread.is_alive()),worker_processes=[p.pid for p in self.children if p.poll() is None])
    def stop_when_idle(self):
        if any(p.poll() is None for p in self.children):raise ValueError('workers remain active; drain before stopping')
        self.stop_requested.set()
        if self.thread:self.thread.join(timeout=2)
