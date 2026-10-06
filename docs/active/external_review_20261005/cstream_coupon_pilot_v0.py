from fractions import Fraction as Q
from dataclasses import dataclass
import json, math

MASS = Q(399623831237000000,5485799090441)
DT = Q(40)
R_MIN = Q(1)


def round_even(q: Q, frac_bits: int) -> int:
    q = q * (1 << frac_bits)
    n, r = divmod(q.numerator, q.denominator)
    return n + int(2*r > q.denominator or (2*r == q.denominator and n % 2 != 0))

@dataclass(frozen=True)
class Obligation:
    name: str
    ok: bool
    detail: str

@dataclass(frozen=True)
class CouponResult:
    value: Q
    obligations: tuple[Obligation, ...]


def safe_zero_times_G(r2: Q, coeff: Q = Q(0)) -> CouponResult:
    # Exact value rewrite is valid only if the original G(r2) expression is defined.
    obligation = Obligation('R2_domain', r2 > R_MIN*R_MIN, f'r2={r2}, require > {R_MIN*R_MIN}')
    if coeff != 0:
        raise NotImplementedError
    return CouponResult(Q(0), (obligation,))


def force_free_stream(q0, p0, steps, checkpoints):
    q = list(q0)
    p = list(p0)
    out = {}
    cdt = DT/MASS
    for s in range(1, steps+1):
        # exact stream update; no history graph
        q = [q[i] + cdt*p[i] for i in range(3)]
        if s in checkpoints:
            out[s] = (tuple(q), tuple(p))
    return tuple(q), tuple(p), out


def state_bit_cost(q,p):
    vals=list(q)+list(p)
    return max(max(abs(x.numerator).bit_length(), x.denominator.bit_length()) for x in vals)

# 1) free-flight bounded working state vs attached DAG retained-history observation
z=(Q(0),Q(0),Q(0)); p=(Q(1),Q(2),Q(3))
qf,pf,cps = force_free_stream(z,p,10000,{10,100,1000,10000})
expected = tuple(10000*DT*Q(k)/MASS for k in (1,2,3))
assert qf == expected and pf == p

# observation schedule invariance: query every step vs sparse checkpoints yields same final exact state
qf2,pf2,_ = force_free_stream(z,p,10000,set(range(1,10001)))
assert (qf2,pf2)==(qf,pf)

# 2) exact-halfway case from attached audit: exact streaming state decides cell without inheriting A's interval dependency
q0=(Q(1,1<<49)-DT/MASS,Q(0),Q(0)); p0=(Q(1),Q(0),Q(0))
q1,p1,_=force_free_stream(q0,p0,1,{1})
assert q1[0]==Q(1,1<<49)
halfway_raw=round_even(q1[0],48)
assert halfway_raw==0

# 3) coupon safety: value can simplify to zero, but domain obligation must survive
coupon = safe_zero_times_G(Q(0),Q(0))
assert coupon.value==0 and not all(o.ok for o in coupon.obligations)

# 4) same coupon on valid domain can be used
coupon_valid=safe_zero_times_G(Q(4),Q(0))
assert all(o.ok for o in coupon_valid.obligations)

report={
  'classification':'C_STREAM_COUPON_TOY_PILOT_V0',
  'scope':'force-free exact rational streaming + obligation-carrying zero*G coupon; no Lang force execution',
  'free_flight_10000':{
      'working_state_scalars':6,
      'max_state_integer_bits':state_bit_cost(qf,pf),
      'final_q':[str(x) for x in qf],
      'sparse_vs_every_step_final_state_identical':True,
      'attached_dag_comparison_note':'attached recheck observed 20,004 retained DAG nodes at 10,000 steps for a different force-free initial condition; this pilot stores only current 6 scalars and checkpoints requested by caller'
  },
  'halfway_case':{
      'q1_exact':str(q1[0]),
      'F48_half_even_raw':halfway_raw,
      'decided':True
  },
  'coupon_domain_obligation':{
      'invalid_r2_zero':{'value':str(coupon.value),'obligation_ok':all(o.ok for o in coupon.obligations),'details':[o.detail for o in coupon.obligations]},
      'valid_r2_four':{'value':str(coupon_valid.value),'obligation_ok':all(o.ok for o in coupon_valid.obligations),'details':[o.detail for o in coupon_valid.obligations]}
  },
  'what_this_does_not_show':[
      'No interacting Lang trajectory was computed',
      'No mpmath interval containment proof was implemented',
      'No wall-time superiority over A/B/C was measured',
      'No production or certification claim'
  ]
}
open('/mnt/data/cstream_coupon_pilot_v0_results.json','w',encoding='utf-8').write(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
