"""Independent scalar/geometry checks and fail-closed publication decisions.

No scalar/executor/electronic-kernel imports. A hash audit is byte provenance,
not physical accuracy. Arithmetic rounding bound is not a deltaH tolerance.
"""
from fractions import Fraction as Q
from pathlib import Path
import hashlib,json,math,os,posixpath
from electronic_pilot.h2_nuclear_v0.check import exact,electronic

BOUND=Q(1,10**75)

def point_geometry(row,requested,snapshot_root=None):
    requested=exact(requested)
    if exact(row['requested_R'])!=requested:raise ValueError('requested geometry')
    g=row['geometry'];actual=g['actual_serialized_R']
    if not isinstance(actual,float) or not math.isfinite(actual) or actual!=float(requested):raise ValueError('actual R')
    if g['actual_R_hex']!=actual.hex() or exact(g['actual_R_exact_decimal'])!=Q.from_float(actual):raise ValueError('actual encoding')
    if abs(exact(g['R_rounding_delta'])-(Q.from_float(actual)-requested))>BOUND:raise ValueError('geometry rounding')
    coords=[[0.,0.,-actual/2],[0.,0.,actual/2]]
    if g['positions_bohr']!=coords or row['actual_stored_positions_bohr']!=coords:raise ValueError('stored geometry')
    if snapshot_root is not None:
        root=posixpath.normpath(str(snapshot_root).replace('\\','/'));origins=row['runtime_module_origins']
        if not origins or 'electronic_pilot.solver' not in origins:raise ValueError('runtime origins missing')
        if any(not posixpath.normpath(path.replace('\\','/')).startswith(root+'/') for path in origins.values()):raise ValueError('checkout import leakage')

def quick(previous,step,mass,snapshot_root):
    m=exact(mass)
    if m<=0:raise ValueError('mass')
    r,p,f=(exact(previous[k]) for k in ('R','P','F'))
    actual_r,actual_p,actual_f=(exact(step[k]) for k in ('R','P','F'))
    if not Q(6,5)<=r<=Q(8,5) or not Q(6,5)<=actual_r<=Q(8,5):raise ValueError('domain')
    if step['dt']!='1' or step['h']!='0.1' or exact(step['mu'])!=m/2:raise ValueError('physical contract')
    if step['energy_conservation_tolerance'] is not None:raise ValueError('energy tolerance promotion')
    half=p+f/2;next_r=r+half/(m/2)
    points=step['points']
    if len(points)!=2:raise ValueError('two stencil points required')
    energies=[]
    for label,row,offset in zip(('left','right'),points,(-Q(1,10),Q(1,10))):
        requested=exact(step['requested_geometries'][label])
        if abs(requested-(next_r+offset))>BOUND or exact(row['requested_R'])!=requested:raise ValueError('requested geometry')
        point_geometry(row,requested,snapshot_root)
        energies.append(electronic(row))
    next_f=(energies[0]-energies[1])*5;next_p=half+next_f/2
    errors={key:abs(exact(step[key])-want) for key,want in (
        ('P_half',half),('R',next_r),('F',next_f),('P',next_p))}
    if any(error>BOUND for error in errors.values()):raise ValueError('integrator/force arithmetic')
    center=step['center_geometry']
    point_geometry(dict(requested_R=step['R'],geometry=center,actual_stored_positions_bohr=center['positions_bohr']),step['R'])
    if step['center_geometry_status']!='SERIALIZATION_ONLY_NOT_ELECTRONICALLY_EVALUATED':raise ValueError('center evaluation promotion')
    n=step['nuclei']
    if exact(n['z_A'])+exact(n['z_B'])!=0 or abs(exact(n['z_B'])-exact(n['z_A'])-actual_r)>BOUND:raise ValueError('COM/individual R')
    if exact(n['p_A'])!=-actual_p or exact(n['p_B'])!=actual_p or exact(n['p_A'])+exact(n['p_B'])!=0:raise ValueError('momentum')
    if exact(n['COM_position'])!=0 or exact(n['total_momentum'])!=0:raise ValueError('reported invariants')
    return dict(status='QUICK_KIT_PASS',arithmetic_only_bound='1e-75',
        force_exact=[next_f.numerator,next_f.denominator],
        errors={k:[v.numerator,v.denominator] for k,v in errors.items()},physical_force_bound=False)

def diagnostic_check(state,center,mass,c0_H,diagnostic,snapshot_root=None):
    if exact(center['requested_R'])!=exact(state['R']):raise ValueError('center identity')
    point_geometry(center,state['R'],snapshot_root)
    e=electronic(center);k=exact(state['P'])**2/exact(mass);h=e+k
    for key,want in [('E_center',e),('K',k),('H_total',h),('delta_H_from_C0',h-exact(c0_H))]:
        if abs(exact(diagnostic[key])-want)>BOUND:raise ValueError('diagnostic arithmetic')
    if diagnostic['status']!='MEASURED' or diagnostic['energy_conservation_tolerance'] is not None:raise ValueError('diagnostic promotion')
    return 'MEASURED_SCALAR_RECOMPUTATION_PASS'

def decide(c0,states,audit_ok,quick_ok):
    success=audit_ok is True and quick_ok is True
    if success and len(states)!=5:raise ValueError('five-step final promotion only')
    return dict(promoted=success,authoritative_state=states[-1] if success else c0,
        state_statuses=['CONFIRMED' if success else 'DISCARDED']*len(states),
        event='CAMPAIGN_CONFIRMED' if success else 'QUICK_KIT_TRIGGERED_STOP' if quick_ok is not True else 'CAMPAIGN_POST_AUDIT_FAILED',
        retry_performed=False,discard_policy='preserve evidence; never delete descendants',
        NOT_CERTIFIED=True,NOT_PRODUCTION_APPROVED=True)

def cadence(cost):
    if isinstance(cost,bool) or not math.isfinite(cost) or cost<0:raise ValueError('audit cost')
    return [dict(K=k,amortized_audit_seconds_per_step=cost/k,maximum_discarded_steps=k,
        status='HYPOTHETICAL_NOT_EXECUTED',chosen=False) for k in (1,5,10,50,100)]

def hostpath(name):
    name=str(name).replace('\\','/')
    if os.name!='nt' and len(name)>2 and name[1:3]==':/':name='/mnt/'+name[0].lower()+name[2:]
    return Path(name)

def sha(path):
    with hostpath(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def verify(bindings):
    for name,expected in bindings.items():
        if not hostpath(name).is_file() or sha(name)!=expected:raise ValueError('BYTE DRIFT '+name)
    return len(bindings)

def persist(path,value):
    encoded=(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf8')
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as stream:stream.write(encoded)
    if json.loads(p.read_bytes())!=value:raise ValueError('state serialization roundtrip')
    return dict(path=p.as_posix(),sha256=sha(p),bytes=len(encoded))
