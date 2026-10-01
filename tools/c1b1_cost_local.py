"""Explicitly authorized Windows execution of the byte-preserved cost harness."""
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time
import types

ROOT=Path(__file__).resolve().parents[1]
SEAL=ROOT/'docs/active/C1B1_KDK20_YOSHIDA40_COST_LOCAL_SEAL_V1.json'


def kernel():
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.GetCurrentProcess.restype=wintypes.HANDLE
    return k,k.GetCurrentProcess()


def windows_affinity(pid):
    if pid!=0:raise ValueError('current process only')
    k,handle=kernel();mask=ctypes.c_size_t();system=ctypes.c_size_t()
    f=k.GetProcessAffinityMask
    f.argtypes=[wintypes.HANDLE,ctypes.POINTER(ctypes.c_size_t),ctypes.POINTER(ctypes.c_size_t)]
    f.restype=wintypes.BOOL
    if not f(handle,ctypes.byref(mask),ctypes.byref(system)):raise ctypes.WinError(ctypes.get_last_error())
    return {i for i in range(ctypes.sizeof(mask)*8) if mask.value&(1<<i)}


def windows_set_affinity(pid,cpus):
    if pid!=0 or not cpus:raise ValueError('current process and nonempty CPU set required')
    k,handle=kernel();f=k.SetProcessAffinityMask
    f.argtypes=[wintypes.HANDLE,ctypes.c_size_t];f.restype=wintypes.BOOL
    if not f(handle,sum(1<<i for i in cpus)):raise ctypes.WinError(ctypes.get_last_error())


def windows_memory(who):
    class Counters(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[
            (name,ctypes.c_size_t) for name in ('PeakWorkingSetSize','WorkingSetSize',
            'QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage',
            'QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
    k,handle=kernel();data=Counters();data.cb=ctypes.sizeof(data)
    f=ctypes.WinDLL('psapi',use_last_error=True).GetProcessMemoryInfo
    f.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD];f.restype=wintypes.BOOL
    if not f(handle,ctypes.byref(data),data.cb):raise ctypes.WinError(ctypes.get_last_error())
    return types.SimpleNamespace(ru_maxrss=data.PeakWorkingSetSize//1024)


def validate(sealed,root=ROOT):
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest()!=sealed['adapter_sha256']:
        raise ValueError('local adapter source hash')
    archive=Path(root)/sealed['archive']
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=sealed['archive_sha256']:
        raise ValueError('local package archive hash')
    return Path(root)/sealed['snapshot']/'code'


def main():
    if sys.platform!='win32':raise SystemExit('this execution adapter is Windows-only')
    sealed=json.loads(SEAL.read_text(encoding='utf-8'));code=validate(sealed)
    os.environ.update(MPMATH_NOGMPY='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
        MKL_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='-1',PYTHONDONTWRITEBYTECODE='1',
        C1B1_EXECUTION_KIND='LOCAL_WINDOWS',C1B1_REMOTE_BENCHMARK='1')
    # The old flag is an execution permit in the preserved harness. Its use is
    # explicitly overridden by the user's local instruction; provenance below
    # records LOCAL_WINDOWS, never REMOTE or Vast.
    os.sched_getaffinity=windows_affinity;os.sched_setaffinity=windows_set_affinity
    sys.modules['resource']=types.SimpleNamespace(RUSAGE_SELF=0,getrusage=windows_memory)
    sys.path.insert(0,str(ROOT))
    sys.path.insert(0,str(code))
    import c1b1_cost_benchmark as bench
    # Child launch uses this adapter too. ROOT/seal/physics code stay unchanged.
    bench.__file__=str(Path(__file__).resolve())
    if sys.argv[1:] == ['campaign']:
        from tools.c1b1_dt40_package import verify
        verified=verify(code.parent)
        selected=sealed['cpu_affinity'];windows_set_affinity(0,{selected})
        environment=dict(execution_kind='LOCAL_WINDOWS',python=sys.version,platform=platform.platform(),
            cpu_affinity=selected,memory_measure='Windows PeakWorkingSetSize / 1024',
            GPU_used=False,legacy_execution_permit=True,source_snapshot_verified=verified,
            start_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
        env_path=ROOT/sealed['run_directory']/'environment.json'
        env_path.write_text(json.dumps(environment,indent=2)+'\n')
        bench.campaign()
    elif len(sys.argv)==7 and sys.argv[1]=='one':
        _,_,method,case,phase,key,cpu=sys.argv
        windows_set_affinity(0,{int(cpu)});payload,original=bench.load()
        row=next(r for r in original['rows'] if r['id']==case)
        expected=next((r for r in bench.read(code/payload['prior_results'])['raw_numerical_summary']['all_results']
            if r['method']==method and r['id']==case and r['dps']==60),None)
        if method=='kdk20' and case=='boundary_pass':
            expected=next(r for r in original['baseline_cause'] if r['dt']==20 and r['dps']==60)
        bench.run_trajectory(method,row,bench.OUT,key,expected,phase)
    else:raise SystemExit('campaign or one method case phase key cpu')


if __name__=='__main__':main()
