"""Host-only CPython PyLong allocation observation; never an execution path."""
import argparse,dis,importlib.util,json,os,subprocess,sys,sysconfig,threading
from collections import Counter
from pathlib import Path
from fractions import Fraction as Q
HERE=Path(__file__).resolve().parent

def build(out):
    from a_numeric_native.harness import find_vcvars
    if sys.implementation.name!='cpython' or sys.version_info[:2]!=(3,12):
        raise RuntimeError('this observation helper requires CPython3.12')
    out.mkdir(parents=True,exist_ok=False)
    source=HERE/'pilot3_alloc_probe.cpp';(out/source.name).write_bytes(source.read_bytes())
    module=out/('pilot3_alloc_probe'+sysconfig.get_config_var('EXT_SUFFIX'))
    inc=sysconfig.get_path('include');lib=Path(sysconfig.get_config_var('installed_base'))/'libs/python312.lib'
    if os.name=='nt':
        script=out/'build.bat'
        script.write_text(f'@call "{find_vcvars()}" >nul\r\n@cl /nologo /O2 /MD /EHsc /std:c++17 /LD /I"{inc}" pilot3_alloc_probe.cpp "{lib}" /link /OUT:"{module.name}"\r\n',encoding='mbcs')
        result=subprocess.run(['cmd','/c',str(script.resolve())],cwd=out,capture_output=True)
    else:result=subprocess.run(['g++','-O2','-std=c++17','-shared','-fPIC','-I'+inc,source.name,'-o',module.name],cwd=out,capture_output=True)
    (out/'build.log').write_bytes(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError(f'allocation observer compile failed; see {out}/build.log')
    spec=importlib.util.spec_from_file_location('pilot3_alloc_probe',module);probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
    return probe

def measure(probe,fn,calls):
    import tracemalloc
    if threading.active_count()!=1 or tracemalloc.is_tracing():raise RuntimeError('single-thread non-tracemalloc observation required')
    return probe.measure(fn,calls)

def operations(fn):
    """Executed Python integer bytecodes and divmod/gcd calls, not heap estimates."""
    if sys.gettrace() or sys.getprofile():raise RuntimeError('existing observation hook')
    counts=Counter();codes={}
    def trace(frame,event,arg):
        if event=='call':
            file=Path(frame.f_code.co_filename).name
            if file in ('c1b1_pilot3_impulse.py','c1b1_fast_impulse.py','profiles.py','fractions.py','pilot3_allocations.py'):
                frame.f_trace_opcodes=True
            return trace
        if event=='opcode':
            code=frame.f_code;ops=codes.setdefault(code,{i.offset:i for i in dis.get_instructions(code)})
            op=ops[frame.f_lasti]
            # old_interval/old_r2 root multiplication is Fraction dispatch; integer
            # work inside fractions.py is counted at the actual integer operation.
            if op.opname=='BINARY_OP':
                if Path(code.co_filename).name=='pilot3_allocations.py' and (code.co_name in ('old_interval','old_r2') or code.co_name=='<genexpr>' and frame.f_back.f_code.co_name=='old_r2') and op.argrepr in ('*','/'):
                    return trace
                counts['integer '+op.argrepr]+=1
        return trace
    def profile(frame,event,arg):
        if event=='c_call' and getattr(arg,'__name__',None) in ('divmod','gcd','isqrt'):
            counts['builtin '+arg.__name__]+=1
    # CPython3.12 enables opcode delivery from existing-frame flags when hooks
    # are installed; arm the current frame before installing either hook.
    current=sys._getframe();previous_opcodes=current.f_trace_opcodes;current.f_trace_opcodes=True
    sys.settrace(trace);sys.setprofile(profile)
    try:value=fn()
    finally:sys.settrace(None);sys.setprofile(None);current.f_trace_opcodes=previous_opcodes
    return value,dict(counts)

def campaign(out):
    from . import pilot3_campaign as P,evidence as E,pilot2_stages as T
    probe=build(out/'native');rows=[]
    cap=next(r for r in P.read(E.HERE/'promotion_inputs.json')['impulses'] if 'precision_target_16384' in r['tags'])
    cases=(
        ('production',48,Q(20),(3<<48,1<<48,-(1<<48)),128),
        ('stress_F150',150,Q(7,11),(3<<150,1,-(5<<150)),256),
        ('large_dt',48,Q(1<<120,13),(3<<48,-1,1),256),
        ('near_raw_limit',48,Q(7,11),((1<<191)-1,-(1<<191),1),256),
        ('actual_cap16384',48,Q(cap['dt']),(10<<48,0,0),16384))
    for label,shift,dt,raw,M in cases:
        values=tuple(Q(v,1<<shift) for v in raw);packet=P.X.RawRelative(raw,shift,values)
        r2=sum(v*v for v in values);dv,inv=P.F._model(r2,M,P.C.L.WORLD_RETARDATION);g=P.F._mul(P.F._neg(dv),inv,M)
        def old_r2():return P.F._radius(sum(v*v for v in values),M)
        def raw_r2():return P.X.radius_raw(sum(v*v for v in raw),shift,M)
        def old_interval():return tuple(sorted((Q(g[0],1<<M)*values[0]*dt,Q(g[1],1<<M)*values[0]*dt)))
        def raw_interval():return P.X.component_interval(g,raw[0],shift,dt,M)
        measurements={}
        for name,fn in (('old_R2_radius',old_r2),('raw_R2_radius',raw_r2),('old_component',old_interval),('raw_component',raw_interval)):
            T.loop(fn,1000);value,ops=operations(fn);counts=measure(probe,fn,5000)
            measurements[name]=dict(value=P.plain(value),operations_per_call=ops,**counts)
        lo,hi,d=raw_interval();assert tuple(Q(v,d) for v in (lo,hi))==old_interval();assert old_r2()==raw_r2()
        rows.append(dict(label=label,shift=shift,dt=str(dt),raw=raw,M=M,G=g,measurements=measurements))
    return dict(rows=rows,scope='actual PyLong objects allocated inside warmed leaf calls (inputs outside); bigint abs_bits>30; storage bytes at allocator request, final bit length at free/end; reserved integer limbs included; helper C++ tracking memory excluded',
                operations_scope='executed integer BINARY_OP and native divmod/gcd/isqrt; observer overhead excluded from performance claims',native_hash=E.sha(out/'native'/('pilot3_alloc_probe'+sysconfig.get_config_var('EXT_SUFFIX'))))

def main():
    from . import evidence as E
    from .pilot3_acceptance import ALLOCATION_SOURCES
    from uuid import uuid4
    sys.set_int_max_str_digits(0) # trusted actual-cap serialization; numeric cap unchanged
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);a=parser.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    source=E.inventory();E.write(a.out/'source.json',source)
    for name in ALLOCATION_SOURCES:
        snapshot=a.out/'source_snapshot'/name;snapshot.parent.mkdir(parents=True,exist_ok=True)
        snapshot.write_bytes((E.ROOT/name).read_bytes());assert E.sha(snapshot)==source[name]
    result=campaign(a.out)
    assert E.inventory()==source
    result.update(source_hash=E.digest(source),input_fingerprint=E.digest([{k:r[k] for k in ('label','shift','dt','raw','M')} for r in result['rows']]),
                  python=sys.version,observation='CPU allocation only; no timing or alternate execution candidate')
    (a.out/'allocations.json').write_text(json.dumps(result,sort_keys=True)+'\n',encoding='utf8')
    names=['allocations.json','source.json','native/pilot3_alloc_probe.cpp','native/build.log',
           'native/pilot3_alloc_probe'+sysconfig.get_config_var('EXT_SUFFIX'),
           *('source_snapshot/'+name for name in ALLOCATION_SOURCES)]
    E.write(a.out/'manifest.json',dict(run_id=str(uuid4()),source_hash=result['source_hash'],
            input_fingerprint=result['input_fingerprint'],outputs={name:E.sha(a.out/name) for name in names}))
if __name__=='__main__':main()
