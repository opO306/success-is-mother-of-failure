"""One host/wrapper for WSL native JC and unchanged Gaussian V5Z."""
from pathlib import Path
import subprocess,time,json,threading
import psutil
from electronic_pilot.h2_stored_root_v1.checker import linux,write

def timed(argv,directory,stdin=None,timeout=600):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    command=['wsl','-e','/usr/bin/time','-f','wall_seconds=%e\npeak_rss_kib=%M\nuser_seconds=%U\nsystem_seconds=%S',
             '-o',linux(directory/'native.time'),'/usr/bin/timeout',str(timeout),
             '/usr/bin/env','OMP_NUM_THREADS=1','OPENBLAS_NUM_THREADS=1','MKL_NUM_THREADS=1',*argv]
    start=time.perf_counter()
    with (directory/'stdout').open('wb') as out,(directory/'stderr').open('wb') as err:
        p=subprocess.run(command,input=stdin,stdout=out,stderr=err,timeout=timeout+30)
    measurement={}
    for line in (directory/'native.time').read_text().splitlines():
        if '=' in line:
            k,v=line.split('=',1);measurement[k]=float(v)
    result=dict(argv=command,exit=p.returncode,outer_wall_seconds=time.perf_counter()-start,
                measurement=measurement,thread_environment='OMP/OPENBLAS/MKL=1',
                scope='GNU time WSL process peak; outer time includes WSL startup')
    write(directory/'process.json',result)
    if p.returncode:raise RuntimeError('native process failed; logs retained')
    return result

class Peak:
    """Sample this Windows controller incl independent HP checker; not global host RSS."""
    def __enter__(self):
        self.peak=0;self.stop=threading.Event();self.proc=psutil.Process()
        def sample():
            while not self.stop.is_set():
                self.peak=max(self.peak,self.proc.memory_info().rss)
                self.stop.wait(.02)
        self.thread=threading.Thread(target=sample,daemon=True);self.thread.start();return self
    def __exit__(self,*args):
        self.stop.set();self.thread.join()
