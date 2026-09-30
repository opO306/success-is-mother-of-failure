"""C1-B1 outgoing outer with energy-based momentum bounds (Energy Bound v0, docs/active/C1B1_ENERGY_BOUND_V0.md).

A new version beside c1b1_outer_chain.certify_outgoing_outer (contract c1b1-outer-bootstrap-tail-v1, unchanged: its
analytic example fixture hashes its sources). Same shells (5/4 split, guard c = b + alpha P_cap + D), same one-step
budgets, same tail packet, same scope (future rounding decisions not certified). What changes:

  * momentum: besides the kick-accumulated [p_lo - 2nK, p_hi + 2nK], the Energy Bound (E2) range of the shell's
    domain at the energy range widened by n one-step budgets -- no accumulation of kicks;
  * q.P floor: besides w_0 - n loss (loss = 2cK + D P_cap - alpha P_floor^2), the angular-momentum identity
    (q.P)^2 = |q|^2 |P|^2 - |q x P|^2 with q.P > 0 and R >= a gives w >= sqrt(a^2 p_lo^2 - L_hi^2). Induction: w_0 >= w_f,
    and w_(k+1) >= w_k - loss >= w_f - loss > 0 (checked) keeps q.P > 0, so the identity gives w_(k+1) >= w_f again
    (R only grows in an outgoing shell, so R >= a).
  * then g_min = 2 alpha (w_f - c K) - 2 c D > 0 and count = ceil((b^2 - R_lo^2)/g_min) as in c1b1_outer_bootstrap.
Not audited: the method is adopted, the theorem is not approved.
"""
from __future__ import annotations

from fractions import Fraction as Q

from a_reference import c1b1_energy_bound as EB
from a_reference import c1b1_outer_bootstrap as O
from a_reference import c1b1_outer_bound as B
from a_reference import c1b1_outer_chain as OC
from a_reference import c1b1_two_atom as C

VERSION = "c1b1-outgoing-energy-v0"
MAX_BUDGET_ROUNDS = 64
NotCertified = O.NotCertified


def _cross(u, v):
    return (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])


def _shell(a, b, entry_lo, p_lo, p_hi, w_lo, L_hi, energy, p_cap):
    c = b + O.ALPHA * p_cap + O.D
    if c >= Q(2 ** 48):
        raise NotCertified("relative guard radius exceeds position profile range")
    domain = O._covered_shell(a, c)
    k = B.H * domain.force / 2 + O.U
    step = B.step_budget(domain, p_cap)
    dE, dL = step["energy_hartree"]["total"], step["angular_bohr_momentum"]["total"]
    n = 1
    for _ in range(MAX_BUDGET_ROUNDS):
        pe = EB.momentum_range(energy.widen(n * dE), domain.radial[0], domain.force)
        if pe is None:
            raise NotCertified("energy forbids this shell")
        if min(p_hi + 2 * n * k, pe[1] + k) > p_cap:
            raise NotCertified("momentum induction budget did not close")
        p_state = max(Q(0), p_lo - 2 * n * k, pe[0])                  # |P_k| lower bound
        p_floor = max(Q(0), p_lo - 2 * n * k, pe[0] - k)              # |P_h| lower bound
        loss = max(Q(0), 2 * c * k + O.D * p_cap - O.ALPHA * p_floor ** 2)
        w_f = w_lo - n * loss
        x = a * a * p_state * p_state - (L_hi + n * dL) ** 2
        if x > 0:
            w_f = max(w_f, O._sqrt_down(x))
        if w_f - loss <= 0:
            raise NotCertified("outgoing q.P floor did not stay positive")
        g_min = 2 * O.ALPHA * (w_f - c * k) - 2 * c * O.D
        if g_min <= 0:
            raise NotCertified("strict outward radial induction did not close")
        count = O.residence_steps(b * b - entry_lo * entry_lo, g_min) if entry_lo < b else 0
        if count <= n:
            break
        n = count
    else:
        raise NotCertified("outgoing energy induction budget did not close")
    p_lo_x = max(Q(0), p_lo - 2 * count * k, pe[0])
    p_hi_x = min(p_hi + 2 * count * k, pe[1])
    totals = {key: {t: count * v for t, v in step[key].items()} for key in ("energy_hartree", "angular_bohr_momentum")}
    return {**O.EXECUTION_SCOPE, "a": a, "b": b, "guard_b": c, "p_cap": p_cap, "induction_budget": n, "max_steps": count,
            "g_min": g_min, "w_floor": w_f, "w_loss_per_step": loss, "half_kick_cap": k, "force_cap": domain.force,
            "L_change_per_step": dL, "energy_step_budget": dE, "energy_entry": (energy.lo, energy.hi),
            "energy_momentum_range": pe, "guard_cells": tuple((s.a, s.b) for s in domain.cells), "step_budget": step,
            "entry_enclosure": {"radius_lower": entry_lo, "p_norm": (p_lo, p_hi), "q_dot_p_lower": w_lo,
                                "L_norm_upper": L_hi},
            "exit_enclosure": {"radius": (b, c), "p_norm": (p_lo_x, p_hi_x), "q_dot_p_lower": w_f - loss,
                               "L_norm_upper": L_hi + count * dL},
            "zero_step_handoff_if_already_beyond_b": True, **totals}


def certify_outgoing_outer_energy(run, p_cap):
    """Stored outgoing state at R >= 20 -> R_J -> analytic tail, with energy-based momentum bounds."""
    p_cap = B.exact(p_cap)
    q, p, snapshot = O._state(run)
    r2 = O._norm2(q)
    entry_lo = O._sqrt_down(r2)
    if entry_lo < 20 or p_cap <= 0:
        raise NotCertified("outgoing outer entry must be at R >= 20")
    if B.sqrt_up(O._norm2(p)) > p_cap:
        raise NotCertified("momentum cap below the current momentum")
    w_lo = O._dot(q, p)
    if w_lo <= 0:
        raise NotCertified("state is not outgoing (q.P <= 0)")
    radius = O.zero_impulse_radius()
    if entry_lo >= radius:
        tail = O.certify_tail(run)
        shells, total, impulse_sum, p_lo = [], 0, Q(0), O._sqrt_down(O._norm2(p))
        energy = EB.energy_of_state(q, p)
    else:
        try:
            j = C.impulse(q, B.H / 2, run.mom)
            if run.J_cache is not None and run.J_cache != j:
                raise NotCertified("initial impulse cache mismatch")
            jump, _ = O._jump(run, C._kick(run.mom, run.atoms, j))
        except C.ExecutorLimitExceeded as error:
            raise NotCertified("initial arithmetic overflow or undecided impulse") from error
        if O.radius_squared_increment(q, jump) <= 0:
            raise NotCertified("initial stored drift does not increase R squared")
        p_hi, p_lo = B.sqrt_up(O._norm2(p)), O._sqrt_down(O._norm2(p))
        L_hi = B.sqrt_up(O._norm2(_cross(q, p)))
        energy = EB.energy_of_state(q, p)
        shells, total, impulse_sum, entry_upper = [], 0, Q(0), B.sqrt_up(r2)
        a = entry_lo
        while a < radius:
            b = min(radius, a * Q(5, 4))
            rec = _shell(a, b, entry_lo, p_lo, p_hi, w_lo, L_hi, energy, p_cap)
            shells.append(rec)
            ex = rec["exit_enclosure"]
            p_lo, p_hi = ex["p_norm"]
            w_lo, L_hi = ex["q_dot_p_lower"], ex["L_norm_upper"]
            energy = energy.widen(rec["max_steps"] * rec["energy_step_budget"])
            total += rec["max_steps"]
            impulse_sum += rec["max_steps"] * rec["half_kick_cap"]
            entry_lo, entry_upper = b, rec["guard_b"]
            a = b
        tail = OC._tail_packet(radius, entry_upper, p_lo, w_lo, p_cap)
    safe_tail_steps = O._check_overflow(run, total, impulse_sum)
    sources = ("position", "momentum_update", "impulse", "discretization", "other_arithmetic")
    finite = {}
    for key in ("energy_hartree", "angular_bohr_momentum"):
        terms = {s: sum((r[key][s] for r in shells), Q(0)) for s in sources}
        finite[key] = {**terms, "total": sum(terms.values(), Q(0))}
    return {**O.EXECUTION_SCOPE, "version": VERSION, "evidence": "analytic_outgoing_outer_energy_shell_composition",
            "profile": dict(O.PROFILE), "model_fingerprint": B.FINGERPRINT, "initial_state": snapshot, "p_cap": p_cap,
            "momentum_bounds": "energy_and_kick", "shells": shells, "tail": tail, "max_steps_to_R_J": total,
            "half_kick_sum_cap": impulse_sum, "final_energy_range": (energy.lo, energy.hi),
            "finite_energy_hartree": finite["energy_hartree"], "angular_bohr_momentum": finite["angular_bohr_momentum"],
            "angular_scope": "finite_entry_to_R_J_only", "safe_additional_FX_tail_steps_lower_bound": safe_tail_steps,
            "global_trajectory_shadowing": "not_claimed", "attainability": "not_proved"}
