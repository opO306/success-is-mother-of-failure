"""Source-separated analytic bounds. See docs/current/C1B1_OUTER_FORMAL_BOUND_V1.md.

No D_valid/fixture access. Finite shell and finite, premise-checked step count only.
Taylor arithmetic encloses derivatives of the frozen PES, not sampled extrema.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction as Q
from math import factorial, isqrt

from a_numeric.exp import enclosure
from a_reference import ar2_lang2024 as L
from a_reference import c1b1_two_atom as C

VERSION = "c1b1-outer-bound-v1"
BITS = 160
MU = C.AR40_MASS_ME / 2
H = Q(40)
UX, UP = Q(1, 2**48), Q(1, 2**80)
FINGERPRINT = C.FROZEN_C1A_FINGERPRINT
if L.parameter_fingerprint() != FINGERPRINT:
    raise ImportError("outer bound requires the frozen C1-A model")


def exact(x) -> Q:
    if isinstance(x, bool) or not isinstance(x, (int, Q)):
        raise TypeError("bound inputs must be exact integers or Fractions")
    return Q(x)


def sqrt_up(x: Q) -> Q:
    x = exact(x)
    if x < 0:
        raise ValueError("negative squared norm")
    n = x * 2**(2 * BITS)
    k = isqrt(n.numerator // n.denominator)
    if Q(k*k) < n:
        k += 1
    return Q(k, 2**BITS)


@dataclass(frozen=True)
class Iv:
    """Exact rational endpoints, every arithmetic result rounded OUTWARD."""
    lo: Q
    hi: Q

    def __post_init__(self):
        lo, hi = exact(self.lo), exact(self.hi)
        if lo > hi:
            raise ValueError("reversed interval")
        object.__setattr__(self, "lo", lo)
        object.__setattr__(self, "hi", hi)

    @classmethod
    def outward(cls, lo, hi):
        s = 2**BITS
        a, b = Q(lo)*s, Q(hi)*s
        return cls(Q(a.numerator // a.denominator, s),
                   Q(-(-b.numerator // b.denominator), s))

    @staticmethod
    def of(x):
        return x if isinstance(x, Iv) else Iv(exact(x), exact(x))

    def __add__(self, other):
        b = Iv.of(other)
        return Iv.outward(self.lo+b.lo, self.hi+b.hi)

    __radd__ = __add__

    def __neg__(self):
        return Iv(-self.hi, -self.lo)

    def __sub__(self, other):
        return self + -Iv.of(other)

    def __rsub__(self, other):
        return Iv.of(other) + -self

    def __mul__(self, other):
        b = Iv.of(other)
        ps = [a*c for a in (self.lo, self.hi) for c in (b.lo, b.hi)]
        return Iv.outward(min(ps), max(ps))

    __rmul__ = __mul__

    def reciprocal(self):
        if self.lo <= 0 <= self.hi:
            raise ValueError("division by an interval containing zero")
        return Iv.outward(1/self.hi, 1/self.lo)

    def exp(self):
        if self.hi > 0:
            raise ValueError("PES EXP arguments must be nonpositive")
        def endpoint(x):
            # exp(-4096) < 2^-160; avoids enormous range reduction in the tail.
            if x <= -4096:
                return Q(0), Q(1, 2**BITS)
            guard = max(0, x.numerator.bit_length()-x.denominator.bit_length()+1)+8
            a, b = enclosure(x, BITS, guard)
            return Q(a, 2**BITS), Q(b, 2**BITS)
        return Iv(endpoint(self.lo)[0], endpoint(self.hi)[1])

    @property
    def magnitude(self):
        return max(abs(self.lo), abs(self.hi))


@dataclass(frozen=True)
class Jet:
    """Interval Taylor coefficients, order 3; coefficient k = derivative/k!."""
    c: tuple[Iv, ...]

    @staticmethod
    def of(x):
        return x if isinstance(x, Jet) else Jet((Iv.of(x), Iv.of(0), Iv.of(0), Iv.of(0)))

    def __add__(self, other):
        b = Jet.of(other)
        return Jet(tuple(a+d for a, d in zip(self.c, b.c)))

    __radd__ = __add__

    def __neg__(self):
        return Jet(tuple(-a for a in self.c))

    def __sub__(self, other):
        return self + -Jet.of(other)

    def __rsub__(self, other):
        return Jet.of(other) + -self

    def __mul__(self, other):
        b = Jet.of(other)
        return Jet(tuple(sum((self.c[k]*b.c[n-k] for k in range(n+1)), Iv.of(0)) for n in range(4)))

    __rmul__ = __mul__

    def reciprocal(self):
        y = [self.c[0].reciprocal()]
        for n in range(1, 4):
            y.append(-y[0]*sum((self.c[k]*y[n-k] for k in range(1, n+1)), Iv.of(0)))
        return Jet(tuple(y))

    def __pow__(self, n: int):
        if n < 0:
            return self.reciprocal() ** -n
        out = Jet.of(1)
        for _ in range(n):
            out = out*self
        return out

    def exp(self):
        y = [self.c[0].exp()]
        for n in range(1, 4):
            y.append(sum((k*self.c[k]*y[n-k] for k in range(1, n+1)), Iv.of(0))*Q(1, n))
        return Jet(tuple(y))


def derivatives(a: Q, b: Q) -> tuple[Iv, ...]:
    """V,V',V'',V''' enclosure for EVERY R in [a,b], frozen retardation ON."""
    a, b = exact(a), exact(b)
    if not 20 <= a <= b:
        raise ValueError("require a finite outer shell 20 <= a <= b")
    r = Jet((Iv(a, b), Iv.of(1), Iv.of(0), Iv.of(0)))
    out = Jet.of(0)
    for name, (short, (eta, cs, kadd)) in L.COMPONENTS.items():
        for alpha, coefs in short.values():
            poly = sum((c*r**k for k, c in coefs.items()), Jet.of(0))
            out += (-alpha*r).exp()*poly
        x = eta*r
        ex = (-x).exp()
        for k, c in cs.items():
            n = 2*k+kadd
            tail = ex*sum((x**j*Q(1, factorial(j)) for j in range(n+1)), Jet.of(0))
            if k == min(cs) and name == "BO":
                num = 1+sum((v*r**(j+1) for j, v in enumerate(L.RET_A)), Jet.of(0))
                den = 1+sum((v*r**(j+1) for j, v in enumerate(L.RET_B)), Jet.of(0))
                damp = num*den.reciprocal()-tail
            elif k == min(cs) and name == "REL":
                damp = -tail
            else:
                damp = 1-tail
            out -= c*damp*r**(-2*k)
    return tuple(out.c[k]*factorial(k) for k in range(4))


@dataclass(frozen=True)
class Shell:
    a: Q
    b: Q
    radial: tuple[Iv, ...] = field(init=False)

    def __post_init__(self):
        a, b = exact(self.a), exact(self.b)
        object.__setattr__(self, "a", a)
        object.__setattr__(self, "b", b)
        object.__setattr__(self, "radial", derivatives(a, b))

    @classmethod
    def prove(cls, a, b):
        a, b = exact(a), exact(b)
        return cls(a, b)

    @property
    def force(self):
        return self.radial[1].magnitude

    @property
    def hessian(self):
        return max(self.radial[2].magnitude, self.force/self.a)

    @property
    def third_directional(self):
        return self.radial[3].magnitude+3*self.radial[2].magnitude/self.a+3*self.force/self.a**2

    def check_segment(self, q0, q1):
        """Check the ENTIRE actual stored-endpoint chord, including its interior."""
        if len(q0) != 3 or len(q1) != 3:
            raise ValueError("three relative position components required")
        q0, q1 = tuple(map(exact, q0)), tuple(map(exact, q1))
        norm2 = lambda q: sum((x*x for x in q), Q(0))
        delta = tuple(y-x for x, y in zip(q0, q1))
        if C.segment_min_R2(q0, delta) < self.a**2 or max(norm2(q0), norm2(q1)) > self.b**2:
            raise ValueError("the whole chord must stay in the proved shell")


def step_budget(shell: Shell, p_half_cap: Q) -> dict:
    """Universal one-step bound with explicit shell/half-momentum premises.

    Returned status does not certify those premises for a trajectory. The initial
    momentum projection is not charged at every step.
    """
    p = exact(p_half_cap)
    if p < 0:
        raise ValueError("negative momentum cap")
    d, u = sqrt_up(Q(3))*UX, sqrt_up(Q(3))*UP/2
    s, f, m3 = H*p/MU, shell.force, shell.third_directional
    energy = {
        "position": f*d+m3*((s+d)**3-s**3)/12,
        "momentum_update": Q(0),
        "impulse": (2*p*u+H*f*u+u*u)/MU,
        "discretization": m3*s**3/12,
        "other_arithmetic": Q(0),
    }
    angular = {"position": d*p, "momentum_update": Q(0),
               "impulse": 2*shell.b*u, "discretization": Q(0), "other_arithmetic": Q(0)}
    return {"version": VERSION, "evidence": "analytic_bound_with_explicit_premises",
            "scope": "one_successful_outer_kdk_step", "energy_quantity": "H-h^2*|F|^2/(8*mu)",
            "profile": {"position": "FX(96,48)", "momentum": "FX(96,80)", "dt": H, "drift": "v2"},
            "premises": {"radial_shell": (shell.a, shell.b), "whole_chord_in_shell": "required",
                         "p_half_norm_le": p, "successful_no_overflow": "required"},
            "model_fingerprint": FINGERPRINT, "enclosure_bits": BITS,
            "derivative_intervals": tuple((v.lo, v.hi) for v in shell.radial),
            "force_cap": f, "third_directional_cap": m3,
            "energy_hartree": {**energy, "total": sum(energy.values(), Q(0))},
            "angular_bohr_momentum": {**angular, "total": sum(angular.values(), Q(0))},
            "physical_energy_endpoint_correction": H**2*f*f/(8*MU)}


def initial_projection_budget(shell: Shell, p_cont_cap: Q) -> dict:
    """One-time projection: position first, then momentum; never a step drift.

    Both position endpoints AND their interpolation must be in shell. p_cont_cap
    bounds the unquantized relative momentum. The force correction depends on
    position only and is included here.
    """
    p = exact(p_cont_cap)
    if p < 0:
        raise ValueError("negative momentum cap")
    d, u = sqrt_up(Q(3))*UX, sqrt_up(Q(3))*UP/2
    e = {"position_initial": (shell.force+H**2*shell.force*shell.hessian/(4*MU))*d,
         "momentum_initial": (2*p*u+u*u)/(2*MU)}
    l = {"position_initial": d*p, "momentum_initial": shell.b*u}
    return {"scope": "initial_projection_only", "energy_hartree": {**e, "total": sum(e.values(), Q(0))},
            "angular_bohr_momentum": {**l, "total": sum(l.values(), Q(0))},
            "premises": {"whole_projection_chord_in_shell": "required", "p_cont_norm_le": p},
            "model_fingerprint": FINGERPRINT}


def finite_sum(budgets: list[dict]) -> dict:
    """Triangle sum for a supplied FINITE list, not a residence-time proof."""
    for b in budgets:
        if b.get("version") != VERSION or b.get("scope") != "one_successful_outer_kdk_step":
            raise ValueError("only this contract's step budgets may be summed")
    sources = ("position", "momentum_update", "impulse", "discretization", "other_arithmetic")
    totals = {}
    for key in ("energy_hartree", "angular_bohr_momentum"):
        terms = {s: sum((b[key][s] for b in budgets), Q(0)) for s in sources}
        totals[key] = {**terms, "total": sum(terms.values(), Q(0))}
    return {"scope": "finite_outer_segments", "steps": len(budgets),
            "premises": [b["premises"] for b in budgets],
            "evidence": "analytic_bound_if_every_segment_premise_holds", **totals}


def example_report() -> dict:
    """Small analytic examples, NO trajectory measurement or D_valid fitting."""
    import hashlib
    from pathlib import Path

    def serial(x):
        if isinstance(x, Q):
            return str(x)
        if isinstance(x, dict):
            return {k: serial(v) for k, v in x.items()}
        if isinstance(x, (tuple, list)):
            return [serial(v) for v in x]
        return x

    root = Path(__file__).resolve().parents[1]
    files = ("a_reference/c1b1_outer_bound.py", "a_reference/ar2_lang2024.py", "a_numeric/exp.py")
    examples = []
    for a, b in ((20, 21), (100, 101), (10000, 10001)):
        shell = Shell.prove(Q(a), Q(b))
        step = step_budget(shell, Q(1))
        init = initial_projection_budget(shell, Q(1))
        sources = step["energy_hartree"]
        examples.append({"step": step, "initial_projection": init,
                         "dominant_rounding_energy_source": max(("position", "impulse"), key=sources.get),
                         "dominant_energy_source_including_discretization":
                             max(("position", "impulse", "discretization"), key=sources.get)})
    return serial({"version": VERSION, "kind": "analytic_examples_not_measurements",
                   "model_fingerprint": FINGERPRINT,
                   "source_sha256": {f: hashlib.sha256((root/f).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                                     for f in files},
                   "examples": examples})


if __name__ == "__main__":
    import json
    import sys
    from pathlib import Path
    report = example_report()
    if len(sys.argv) == 2:
        Path(sys.argv[1]).write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    else:
        print(json.dumps(report, indent=2))
