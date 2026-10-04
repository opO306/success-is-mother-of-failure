"""Prepared Generation 1 lifetime contracts; no numerical kernel or answer cache.

The frozen model is hashed at world preparation only. Hot guards compare immutable
parameter views and implementation identities, never hash or normalize rationals.
Changing a frozen world requires a new reviewed model; stale bindings fail closed.
Run coefficients may be explicitly rebound after a supported metadata change.
"""
from dataclasses import dataclass, field
from fractions import Fraction as Q
from types import MappingProxyType
from a_numeric import profiles as N
from . import ar2_lang2024 as L, c1b1_two_atom as C

ROUNDING_CONTRACT = 'fx-nearest-ties-even-v1'


def _exact_pair(value):
    if (type(value) is not Q or type(value.numerator) is not int or
        type(value.denominator) is not int or value.denominator<=0):
        raise C.ContractViolation('stale prepared binding: exact ratio type')
    return value.numerator,value.denominator


@dataclass(frozen=True,slots=True,eq=False)
class _FrozenScalar:
    value: object

    def __hash__(self):
        return hash(self.value)

    def __eq__(self,other):
        if type(other) is not type(self.value):return False
        if type(other) is Q:
            if type(other.numerator) is not int or type(other.denominator) is not int:return False
        return other==self.value


@dataclass(frozen=True,slots=True)
class _FrozenList:
    values: tuple

    def __eq__(self,other):
        return type(other) is list and tuple(other)==self.values


def _freeze(value):
    if type(value) is dict:
        # Typed keys distinguish integer exponent 3 from equal-valued float 3.0.
        return MappingProxyType({_freeze(k):_freeze(v) for k,v in value.items()})
    if type(value) is tuple:
        return tuple(_freeze(v) for v in value)
    if type(value) is list:
        return _FrozenList(tuple(_freeze(v) for v in value))
    if type(value) is Q:
        # Fraction's private slots can be mutated by trusted Python code. Never
        # alias the source coefficient: a private-slot fault must compare unequal.
        return _FrozenScalar(Q(*_exact_pair(value)))
    if type(value) not in (str,int,bool,Q):
        raise C.ContractViolation('unsupported prepared binding parameter')
    return _FrozenScalar(value)


def _implementations():
    # Code identity also catches replacing __code__ on an existing function.
    functions=(N._div_round,)+tuple(getattr(N.FixedPoint,n) for n in
                    ('from_exact','to_exact','add','valid_raw','_check'))
    return tuple((f,f.__code__) for f in functions)


def _kernels():
    from . import c1b1_impulse_primitives as IP,c1b1_pilot3_impulse as X,c1b1_fast_impulse as F,c1b1_combined_arithmetic as K
    modules=((IP,('_mul','_add','_neg','_const','_scale','_div_small','_div_pos',
                  '_taylor_side','_exp_side','_exp_neg','_const_cache','_raw_powers','_inverse_table','_radius')),
             (F,('_impulse_model_R_fast','_model','_mul','_add','_neg','_scale','_div_small','_div_pos','_exp_neg','_const_cache','_inverse_table','_radius','impulse')),
             (X,('pair','const_pair','_scale','grid_constants','relative_raw','radius_raw','exact_dt_pair',
                 'component_interval','round_operands','decide_raw','impulse_raw','model_prepared',
                 '_mul','_add','_neg','_div_small','_div_pos','_exp_neg','_inverse_table','isqrt')),
             (K,('canonical_fx','drift','prepare_drift','kick','_checked_sum')),
             (K.DriftConversionContract,('assert_current','_ratio','_rounded','ratio','rounded')),
             (C,('segment_min_R2','_limit','exact','drift_momentum','relative','displacement','_kick','_drift','_decide','Atom')),
             (C.Atom,('__init__',)))
    return tuple((module,name,fn,getattr(fn,'__wrapped__',fn),getattr(getattr(fn,'__wrapped__',fn),'__code__',None))
                 for module,names in modules for name in names for fn in (getattr(module,name),))


@dataclass(frozen=True,slots=True)
class WorldKey:
    parameter_fingerprint: str
    model_contract: str
    step_contract: str
    rounding_contract: str
    retardation: bool


@dataclass(frozen=True,slots=True)
class WorldBinding:
    key: WorldKey
    _components: object = field(repr=False)
    _scalars: tuple = field(repr=False)
    _implementations: tuple = field(repr=False)
    _fingerprinter: object = field(repr=False)
    _prepared: tuple = field(repr=False)
    _round_aliases: tuple = field(repr=False)
    _kernels: tuple = field(repr=False)
    _ln2: object = field(repr=False)
    _candidate_cache: tuple = field(repr=False)

    @classmethod
    def build(cls):
        from . import c1b1_pilot3_impulse as X, c1b1_combined_arithmetic as K
        from . import c1b1_impulse_primitives as IP
        fingerprint=L.parameter_fingerprint()
        if fingerprint!=C.FROZEN_C1A_FINGERPRINT:
            raise C.ContractViolation('stale prepared binding: frozen physics fingerprint')
        key=WorldKey(fingerprint,L.CONTRACT_VERSION,C.CONTRACT_VERSION,
                     ROUNDING_CONTRACT,L.WORLD_RETARDATION)
        handle=cls(key,_freeze(L.COMPONENTS),
                   _freeze((L.BOHR_ANGSTROM,L.R_MIN_ANGSTROM,L.R_MIN_BOHR,C.R_MIN2,
                    L.RET_A,L.RET_B,getattr(N,'PREPARED_ROUNDING_CONTRACT',False),
                    L.CONTRACT_VERSION,C.CONTRACT_VERSION,ROUNDING_CONTRACT,
                    L.WORLD_RETARDATION,C.FROZEN_C1A_FINGERPRINT)),
                   _implementations(),L.parameter_fingerprint,
                   (X.WORLD,X.RET_A,X.RET_B),(K._div_round,X._div_round),_kernels(),
                   _freeze(IP.LN2_UPPER),
                   tuple((M,_freeze(IP._const_cache.__wrapped__(M))) for M in
                         (128,256,512,1024,2048,4096,8192,16384)))
        # Prepared values must originate from the current frozen parameter source.
        if X.WORLD!=X.prepare_world() or X.RET_A!=tuple((X.pair(a),X.pair(a*(i+1))) for i,a in enumerate(L.RET_A)) or X.RET_B!=tuple((X.pair(b),X.pair(b*(i+1))) for i,b in enumerate(L.RET_B)):
            raise C.ContractViolation('stale prepared binding: prepared world')
        handle.assert_current(check_base_cache=True)
        return handle

    def assert_current(self,*,check_base_cache=False):
        from . import c1b1_pilot3_impulse as X, c1b1_combined_arithmetic as K
        from . import c1b1_impulse_primitives as IP
        k=self.key
        if (L.parameter_fingerprint is not self._fingerprinter or
            C.FROZEN_C1A_FINGERPRINT!=k.parameter_fingerprint or
            (L.CONTRACT_VERSION,C.CONTRACT_VERSION,ROUNDING_CONTRACT,L.WORLD_RETARDATION)!=
            (k.model_contract,k.step_contract,k.rounding_contract,k.retardation) or
            type(L.COMPONENTS) is not dict or L.COMPONENTS!=self._components or
            (L.BOHR_ANGSTROM,L.R_MIN_ANGSTROM,L.R_MIN_BOHR,C.R_MIN2,L.RET_A,L.RET_B,
             getattr(N,'PREPARED_ROUNDING_CONTRACT',False),L.CONTRACT_VERSION,
             C.CONTRACT_VERSION,ROUNDING_CONTRACT,L.WORLD_RETARDATION,
             C.FROZEN_C1A_FINGERPRINT)!=self._scalars or
            _implementations()!=self._implementations or
            any(a is not b for a,b in zip((X.WORLD,X.RET_A,X.RET_B),self._prepared)) or
            (K._div_round,X._div_round)!=self._round_aliases or IP.LN2_UPPER!=self._ln2 or
            any(getattr(module,name) is not fn or getattr(fn,'__wrapped__',fn) is not body or
                getattr(body,'__code__',None) is not code for module,name,fn,body,code in self._kernels)):
            raise C.ContractViolation('stale prepared binding: world or rounding')
        if check_base_cache and any(IP._const_cache(M)!=sealed for M,sealed in self._candidate_cache):
            raise C.ContractViolation('stale prepared binding: mutable Candidate B cache')


_WORLD=None


def world_binding():
    global _WORLD
    if _WORLD is None:
        _WORLD=WorldBinding.build()
    else:
        _WORLD.assert_current()
    return _WORLD


@dataclass(frozen=True,slots=True)
class RunKey:
    world: WorldKey
    mode: str
    dt_ratio: tuple
    species: tuple
    mass_ratios: tuple
    position_profile: tuple
    momentum_profile: tuple
    drift: str
    precision_policy: tuple

    @property
    def dt(self):
        return Q(*self.dt_ratio)


@dataclass(frozen=True,slots=True)
class RunBinding:
    key: RunKey
    world: WorldBinding
    _run: object = field(repr=False,compare=False)
    _pos: object = field(repr=False,compare=False)
    _mom: object = field(repr=False,compare=False)
    _initial_cache: tuple | None = field(default=None,repr=False,compare=False)

    @classmethod
    def build(cls,run,mode):
        from .c1b1_combined_arithmetic import canonical_fx
        ps,ms=canonical_fx(run.pos),canonical_fx(run.mom)
        if ps is None or ms is None or type(run.dt) is not Q:
            raise C.ContractViolation('unsupported prepared binding Run')
        world=world_binding();species=tuple(a.species for a in run.atoms)
        if type(C.START_PRECISION_BITS) is not int or type(C.MAX_PRECISION_BITS) is not int:
            raise C.ContractViolation('stale prepared binding: precision policy type')
        key=RunKey(world.key,mode,_exact_pair(run.dt),species,
                   tuple(_exact_pair(C.SPECIES_MASS[s]) for s in species),
                   ps,ms,run.drift,(C.START_PRECISION_BITS,C.MAX_PRECISION_BITS))
        handle=cls(key,world,run,run.pos,run.mom)
        # A declared initial-state cache is part of the original REF input contract
        # (including boundary fault fixtures). Capture it only at t_steps=0.
        if run.J_cache is not None and run.t_steps==0 and not hasattr(run,'_c1b1_impulse_binding'):
            handle=cls(key,world,run,run.pos,run.mom,handle._cache_inputs(run))
        handle.assert_cached_impulse(run)
        return handle

    def _cache_inputs(self,run):
        k=self.key
        return (k.world,k.dt_ratio,k.species,k.mass_ratios,k.position_profile,k.momentum_profile,
                k.drift,k.precision_policy,tuple(a.r for a in run.atoms),run.J_cache)

    def assert_cached_impulse(self,run):
        if run.J_cache is None:return
        inputs=self._cache_inputs(run)
        if (getattr(run,'_c1b1_impulse_binding',None)!=inputs and
            not (run.t_steps==0 and self._initial_cache==inputs)):
            raise C.ContractViolation('stale prepared binding: cached impulse; clear J_cache before rebind')

    def record_cached_impulse(self,run):
        if run.J_cache is not None:
            run._c1b1_impulse_binding=self._cache_inputs(run)

    def assert_current(self,run,mode):
        from .c1b1_combined_arithmetic import canonical_fx
        k=self.key
        if (run is not self._run or mode!=k.mode or run.pos is not self._pos or
            run.mom is not self._mom or type(run.dt) is not Q or
            _exact_pair(run.dt)!=k.dt_ratio or
            tuple(a.species for a in run.atoms)!=k.species or
            any(C.SPECIES_MASS.get(s) is None or
                _exact_pair(C.SPECIES_MASS[s])!=mass
                for s,mass in zip(k.species,k.mass_ratios)) or
            canonical_fx(run.pos)!=k.position_profile or canonical_fx(run.mom)!=k.momentum_profile or
            run.drift!=k.drift or type(C.START_PRECISION_BITS) is not int or
            type(C.MAX_PRECISION_BITS) is not int or
            (C.START_PRECISION_BITS,C.MAX_PRECISION_BITS)!=k.precision_policy):
            raise C.ContractViolation('stale prepared binding: Run, mode or coefficients')
        self.world.assert_current(check_base_cache=mode in ('fast_combined','fast_pilot3:B','fast_pilot3:BC','fast_pilot3:BCD'))
        self.assert_cached_impulse(run)
