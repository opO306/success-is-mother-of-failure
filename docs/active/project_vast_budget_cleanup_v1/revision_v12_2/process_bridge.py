"""Read adapter bootstrap for existing supervisor/guardian, preserving their STOP code."""
from pathlib import Path
import sys,subprocess,runpy,json,os,time
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'revision_v12/transport'

def install_dispatch():
    previous=subprocess.Popen
    def popen(argv,*args,**kwargs):
        if isinstance(argv,(list,tuple)) and len(argv)>2 and Path(str(argv[2])).resolve() in ((OLD/'supervisor.py').resolve(),(OLD/'guardian_driver.py').resolve()):
            target=Path(str(argv[2])).stem
            argv=[argv[0],'-B',str(HERE/'process_bridge.py'),target,*argv[3:]]
        return previous(argv,*args,**kwargs)
    subprocess.Popen=popen

def main():
    mode=sys.argv[1]
    if mode not in ('supervisor','guardian_driver'):raise ValueError('EXACT_EXISTING_PROCESS_ENTRY')
    sys.path.insert(0,str(HERE));sys.path.insert(1,str(OLD));sys.path.insert(2,str(OLD.parent))
    from time_authority import require_extension
    grant=require_extension()
    from transport_reads import checked_class
    import state_contract
    # STOP observation can use the full absolute window, never extend caller's <=12s.
    path_arg='--lease' if mode=='supervisor' else '--out'
    out=Path(sys.argv[sys.argv.index(path_arg)+1]);out=out.parent if mode=='supervisor' else out
    def log(value):
        with (out/'v12_2_read_events.jsonl').open('ab') as f:f.write(json.dumps(dict(value,pid=os.getpid(),monotonic_ns=time.monotonic_ns()),sort_keys=True).encode()+b'\n');f.flush();os.fsync(f.fileno())
    state_contract.CheckedCli=checked_class(state_contract,grant['absolute_end_monotonic_ns']/1e9,log)
    install_dispatch()
    sys.argv=[str(OLD/(mode+'.py')),*sys.argv[2:]]
    runpy.run_path(str(OLD/(mode+'.py')),run_name='__main__')

if __name__=='__main__':main()
