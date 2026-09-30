"""C1-B1 Energy Bound v0: the shared energy-based momentum range and the energy-barrier shell lemma.

Design and derivation: docs/active/C1B1_ENERGY_BOUND_V0.md (designer verdict 2026-09-30: adopt the method; the method is
not an approved theorem until derived, implemented, fault-injected and independently audited). Never changes A, the
executor, D_valid or the outgoing code; it reads the frozen PES through the same interval arithmetic as
c1b1_outer_bound.

Quantities (relative coordinates): q, P = (p_j - p_i)/2, mu = m/2, R = |q|, H = |P|^2/(2 mu) + V(R),
E~ = H - h^2 V'(R)^2/(8 mu) (the modified energy c1b1_outer_bound bounds per step).

(E1) Energy range. For a stored state, E~ is enclosed from the exact |P|^2 and the enclosures of V and V' at R.
     After n successful steps whose one-step premises hold (chord in a proved shell, |P_h| <= P_cap), E~ stays within
     the initial range widened by the sum of the one-step budgets (c1b1_outer_bound.step_budget energy total).
(E2) Momentum range. If R lies in a radial cell where V in [V_lo, V_hi] and |V'| <= F, and E~ in [E_lo, E_hi], then
         |P|^2 = 2 mu (E~ - V) + h^2 V'^2 / 4   lies in   [2 mu (E_lo - V_hi), 2 mu (E_hi - V_lo) + h^2 F^2 / 4].
     If the upper end is negative, no state with that energy is in the cell (energetically forbidden).
     No kick is accumulated: the range depends only on the energy range and on where the state is.
(E3) Energy-barrier shell. Let every cell of [c, d] be forbidden for E~ <= E_hi, and d - c > alpha P_h_cap + D. Take a
     successful step from a stored state with R_n >= d and |P_h| <= P_h_cap to a stored state with E~ <= E_hi. Then
     R_(n+1) >= d: the stored displacement is at most alpha |P_h| + D < d - c, so R_(n+1) > c, and R_(n+1) is not in
     [c, d) because no state with E~ <= E_hi is there. (The premises -- that E~ <= E_hi after the step and the bound on
     |P_h| -- are the CALLER's to prove; the lemma does not say that any trajectory satisfies them.)
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction as Q
from functools import lru_cache
from math import factorial

from a_reference import ar2_lang2024 as L
from a_reference import c1b1_outer_bootstrap as O
from a_reference import c1b1_outer_bound as B

VERSION = "c1b1-energy-bound-v0"


@lru_cache(maxsize=4096)
def radial_derivatives(a: Q, b: Q) -> tuple:
    """V, V', V'', V''' enclosures for EVERY R in [a, b], 0 < a <= b, frozen retardation ON.

    The body is c1b1_outer_bound.derivatives verbatim except its scope guard 20 <= a: the same Taylor-interval
    arithmetic is valid for any R > 0 (tests compare the source text and the values on R >= 20). Below R ~ 5 the
    enclosures get very wide (Tang-Toennies damping cancellation, docs/active/C1B1_FIELD_MAP_SURVEY_V0.md 2.4): wide is
    still sound, only useless."""
    a, b = B.exact(a), B.exact(b)
    if not 0 < a <= b:
        raise ValueError("require 0 < a <= b")
    r = B.Jet((B.Iv(a, b), B.Iv.of(1), B.Iv.of(0), B.Iv.of(0)))
    out = B.Jet.of(0)
    for name, (short, (eta, cs, kadd)) in L.COMPONENTS.items():
        for alpha, coefs in short.values():
            poly = sum((c*r**k for k, c in coefs.items()), B.Jet.of(0))
            out += (-alpha*r).exp()*poly
        x = eta*r
        ex = (-x).exp()
        for k, c in cs.items():
            n = 2*k+kadd
            tail = ex*sum((x**j*Q(1, factorial(j)) for j in range(n+1)), B.Jet.of(0))
            if k == min(cs) and name == "BO":
                num = 1+sum((v*r**(j+1) for j, v in enumerate(L.RET_A)), B.Jet.of(0))
                den = 1+sum((v*r**(j+1) for j, v in enumerate(L.RET_B)), B.Jet.of(0))
                damp = num*den.reciprocal()-tail
            elif k == min(cs) and name == "REL":
                damp = -tail
            else:
                damp = 1-tail
            out -= c*damp*r**(-2*k)
    return tuple(out.c[k]*factorial(k) for k in range(4))


@dataclass(frozen=True)
class EnergyRange:
    """E~ in [lo, hi] (hartree), exact rationals."""
    lo: Q
    hi: Q

    def widen(self, x: Q) -> "EnergyRange":
        if x < 0:
            raise ValueError("negative widening")
        return EnergyRange(self.lo - x, self.hi + x)


def _square_range(iv) -> tuple:
    lo2, hi2 = iv.lo * iv.lo, iv.hi * iv.hi
    return (Q(0) if iv.lo <= 0 <= iv.hi else min(lo2, hi2)), max(lo2, hi2)


def energy_of_state(q, p) -> EnergyRange:
    """(E1) for one stored relative state (exact q, P)."""
    r2 = O._norm2(q)
    d = radial_derivatives(O._sqrt_down(r2), B.sqrt_up(r2))
    kinetic = O._norm2(p) / (2 * B.MU)
    f2_lo, f2_hi = _square_range(d[1])
    c = B.H ** 2 / (8 * B.MU)
    return EnergyRange(kinetic + d[0].lo - c * f2_hi, kinetic + d[0].hi - c * f2_lo)


def energy_of_packet(r_lo, r_hi, p_lo, p_hi) -> EnergyRange:
    """(E1) for any state with R in [r_lo, r_hi] and |P| in [p_lo, p_hi]."""
    d = radial_derivatives(r_lo, r_hi)
    f2_lo, f2_hi = _square_range(d[1])
    c = B.H ** 2 / (8 * B.MU)
    return EnergyRange(p_lo ** 2 / (2 * B.MU) + d[0].lo - c * f2_hi, p_hi ** 2 / (2 * B.MU) + d[0].hi - c * f2_lo)


def momentum_range(energy: EnergyRange, V, F: Q):
    """(E2): (p_lo, p_hi) for a state with R in a cell where V in the interval V and |V'| <= F, or None if the cell is
    energetically forbidden (no such state exists)."""
    hi2 = 2 * B.MU * (energy.hi - V.lo) + B.H ** 2 * F * F / 4
    if hi2 < 0:
        return None
    lo2 = 2 * B.MU * (energy.lo - V.hi)
    return (O._sqrt_down(lo2) if lo2 > 0 else Q(0)), B.sqrt_up(hi2)


def certify_energy_barrier(E_hi: Q, c: Q, d: Q, p_half_cap: Q, cells: int) -> dict:
    """(E3): check that [c, d], split into `cells` equal cells (a fixed rule chosen by the caller, never fitted to a
    trajectory), is energetically forbidden for E~ <= E_hi and thicker than one stored step with |P_h| <= p_half_cap.
    Raises O.NotCertified otherwise."""
    c, d, E_hi, p_half_cap = map(B.exact, (c, d, E_hi, p_half_cap))
    if type(cells) is not int or cells < 1 or not 0 < c < d or p_half_cap < 0:
        raise ValueError("need 0 < c < d, a positive cap and a positive integer cell count")
    step = O.ALPHA * p_half_cap + O.D
    if not d - c > step:
        raise O.NotCertified("barrier is not thicker than one stored step")
    margins = []
    for i in range(cells):
        a, b = c + (d - c) * i / cells, c + (d - c) * (i + 1) / cells
        V, V1 = radial_derivatives(a, b)[:2]
        hi2 = 2 * B.MU * (E_hi - V.lo) + B.H ** 2 * V1.magnitude ** 2 / 4
        if hi2 >= 0:
            raise O.NotCertified("a barrier cell is not energetically forbidden")
        margins.append((a, b, V.lo))
    return {"version": VERSION, "evidence": "energy_barrier_shell", "barrier": (c, d), "E_tilde_upper": E_hi,
            "p_half_cap": p_half_cap, "max_stored_step": step, "cells": tuple(margins),
            "V_lower_min": min(m[2] for m in margins),
            "statement": "a successful step from a stored state with R >= d and |P_h| <= p_half_cap whose next stored "
                         "state has E~ <= E_hi leaves that state at R >= d",
            "premises_not_proved_here": ("E~ <= E_hi after every step of the trajectory",
                                         "|P_h| <= p_half_cap at every step taken from R >= d")}
