"""OS-backed worker fencing, only for isolated processes and fixtures."""
import os,threading
from pathlib import Path
from contextlib import contextmanager
_guard=threading.Lock();_locks={}

class Fence:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with _guard:self.thread=_locks.setdefault(str(self.path.resolve()),threading.Lock())
        self.handle=None
    def acquire(self):
        if not self.thread.acquire(blocking=False):return False
        try:
            self.handle=self.path.open('a+b');self.handle.seek(0,2)
            if not self.handle.tell():self.handle.write(b'0');self.handle.flush()
            self.handle.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.handle.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            return True
        except OSError:
            if self.handle:self.handle.close();self.handle=None
            self.thread.release();return False
    def release(self):
        if not self.handle:return
        self.handle.seek(0)
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(self.handle.fileno(),msvcrt.LK_UNLCK,1)
        else:
            import fcntl
            fcntl.flock(self.handle.fileno(),fcntl.LOCK_UN)
        self.handle.close();self.handle=None;self.thread.release()

@contextmanager
def claimed_worker(lab,owner,root):
    maintenance=Fence(Path(root)/'maintenance.lock')
    # Brief contention is queueing, not a worker failure.
    import time
    while not maintenance.acquire():time.sleep(.01)
    fence=None
    try:
        job=lab.claim(owner)
        if job is not None:
            fence=Fence(Path(root)/(job+'.worker.lock'))
            if not fence.acquire():raise RuntimeError('worker fence already owned; do not run')
    finally:maintenance.release()
    try:yield job
    finally:
        if fence:fence.release()

def recover_if_no_workers(lab,root):
    maintenance=Fence(Path(root)/'maintenance.lock');held=[]
    if not maintenance.acquire():return False
    try:
        for job in lab.snapshot()['jobs']:
            f=Fence(Path(root)/(job['id']+'.worker.lock'))
            if not f.acquire():return False
            held.append(f)
        lab.recover_after_workers_stopped(workers_stopped=True);return True
    finally:
        for f in reversed(held):f.release()
        maintenance.release()
