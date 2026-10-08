"""Linux RSS/deadline watcher, sampled every second; external guardian is the host failsafe."""
import os
import signal
import threading
import time
import psutil


class Watch:
    def __init__(self,deadline,control_check=None):
        self.deadline=deadline; self.control_check=control_check; self.done=threading.Event(); self.reason=None
    def start(self):
        def failed(signum,frame): raise RuntimeError(self.reason or 'RESOURCE_MONITOR_STOP')
        self.old=signal.signal(signal.SIGUSR1,failed)
        self.thread=threading.Thread(target=self.poll,daemon=True); self.thread.start()
    def poll(self):
        proc=psutil.Process()
        while not self.done.wait(1):
            try:
                if self.control_check is not None: self.control_check()
                members=[proc,*proc.children(recursive=True)]
                rss=0
                for member in members:
                    try: rss+=member.memory_info().rss
                    except psutil.NoSuchProcess: pass
                if rss>2048*1024**2: self.reason='AGGREGATE_RSS_CAP_STOP'
                if time.monotonic()>=self.deadline: self.reason='COMPUTE_DEADLINE_STOP'
            except Exception:
                self.reason='RESOURCE_MONITOR_UNCONFIRMED_STOP'
            if self.reason:
                os.kill(os.getpid(),signal.SIGUSR1); return
    def close(self):
        self.done.set(); self.thread.join(timeout=2); signal.signal(signal.SIGUSR1,self.old)
