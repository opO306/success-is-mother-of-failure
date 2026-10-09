"""V12.3 subprocess entry bridge for the unchanged V12 watchdog, supervisor and guardian driver.

Each bridged process gets the same read-only retry and V12.3 approval functions, then runs the original
V12 file with runpy. STOP/destroy/mutation code paths are the originals.
"""
from pathlib import Path
import json,os,runpy,subprocess,sys,time

HERE=Path(__file__).resolve().parent
V12=HERE.parent/'revision_v12'
V12_2=HERE.parent/'revision_v12_2'
TARGETS={'watchdog':V12/'watchdog.py','supervisor':V12/'transport/supervisor.py','guardian_driver':V12/'transport/guardian_driver.py'}


def paths():
    """V12 modules first; V12.2 only appended so its preflight/process_bridge never shadow V12 names."""
    for p in (str(V12),str(V12/'transport'),str(HERE)):
        if p in sys.path:sys.path.remove(p)
    sys.path[:0]=[str(HERE),str(V12/'transport'),str(V12)]
    if str(V12_2) not in sys.path:sys.path.append(str(V12_2))


def install_dispatch(previous=None):
    previous=previous or subprocess.Popen
    resolved={Path(p).resolve():name for name,p in TARGETS.items()}
    def popen(argv,*args,**kwargs):
        if isinstance(argv,(list,tuple)) and len(argv)>2:
            try:target=resolved.get(Path(str(argv[2])).resolve())
            except (OSError,ValueError):target=None
            if target:argv=[argv[0],'-B',str(HERE/'process_bridge.py'),target,*argv[3:]]
        return previous(argv,*args,**kwargs)
    popen.v12_3_dispatch=True
    subprocess.Popen=popen
    return popen


def main():
    mode=sys.argv[1]
    if mode not in TARGETS:raise ValueError('EXACT_EXISTING_PROCESS_ENTRY')
    paths()
    import authority;authority.install()
    if mode=='watchdog':
        import lifecycle
        from reads import ReadRetryProvider
        lifecycle.Provider=ReadRetryProvider  # watchdog.py does `from lifecycle import Provider` after this point.
        import closure;closure.install()
    else:
        from transport_reads import checked_class
        import state_contract
        path_arg='--lease' if mode=='supervisor' else '--out'
        out=Path(sys.argv[sys.argv.index(path_arg)+1]);out=out.parent if mode=='supervisor' else out
        def log(value):
            with (out/'v12_3_read_events.jsonl').open('ab') as f:
                f.write(json.dumps(dict(value,pid=os.getpid(),monotonic_ns=time.monotonic_ns()),sort_keys=True).encode()+b'\n');f.flush();os.fsync(f.fileno())
        # Retry stays inside each caller's own CheckedCli.timeout_seconds; no extra absolute window.
        state_contract.CheckedCli=checked_class(state_contract,float('inf'),log)
        install_dispatch()
    sys.argv=[str(TARGETS[mode]),*sys.argv[2:]]
    runpy.run_path(str(TARGETS[mode]),run_name='__main__')


if __name__=='__main__':main()
