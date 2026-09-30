"""C1-B1 inbound V1: outer inbound (R >= 20, moving in) to the inner handoff. Never changes A, D_valid or the outgoing code.

Design, derivation and scope: docs/active/C1B1_INBOUND_V1.md (designer verdicts IN-1..IN-4 on inbound V0, 2026-09-30).
It REUSES the outgoing contract's pieces -- the one-step bounds (c1b1_outer_bound.step_budget), the force envelope, the
covered shells, R_J, the packet form and NotCertified -- but NOT the outgoing shell theorem: time reversal maps a forward
inbound orbit to a backward outgoing one, so the inward induction below is its own (mirror) inequality set.

(Z) R >= R_J. Every half kick is exactly raw 0 (c1b1_outer_bootstrap section 5: h F_bar(R_J) < u_p, positions only).
    Momenta and the stored per-atom displacements are constant, q_n = q_0 + n delta exactly. The first n with
    |q_n|^2 < R_J^2 is found exactly (a quadratic in n). Its state carries the one nonzero kick at q_n: |J| <= K_Z.
(S) Mirror shell [a, b), a - g >= 20, g = alpha P_cap + D. Entry R <= R_hi <= b, w = q.P <= W < 0,
    |P| in [p_lo, p_hi], |L| <= L_hi (L = q x P). For k < N while R_k >= a (before the exit):
        |P_k| in [p_lo - 2 k K, p_hi + 2 k K],  p_hi + 2 N K <= P_cap         (each half kick |J| <= K = h F/2 + U)
        |L_k| <= L_hi + k dL                          (dL: c1b1_outer_bound.step_budget's one-step angular total)
        w_(k+1) <= w_k + gain,  gain = 2 b K + alpha P_cap^2 + D P_cap
            (a half kick moves q.P by at most |q| K <= b K; the drift adds alpha |P_h|^2 + d.P_h to q.P_h)
        w_k <= w_c = min(W + N gain, -sqrt(a^2 p_lo(N)^2 - L_hi(N)^2))   (the root only when real)
            by (q.P)^2 = |q|^2 |P|^2 - |q x P|^2 with q.P < 0 and R >= a: w_0 <= w_c, and w_(k+1) <= w_c + gain < 0
            (checked) keeps q.P < 0, so the identity gives w_(k+1) <= w_c again while R >= a
        R_(k+1)^2 - R_k^2 = 2 q_k.delta + |delta|^2 <= 2 alpha (w_c + b K) + c0 =: -g_in < 0 (checked),
            c0 = 2 b D + (alpha P_cap + D)^2
    So R^2 falls by at least g_in per step and R < a after at most count = floor((R_hi^2 - a^2)/g_in) + 1 <= N steps
    (N found by N <- count until count <= N). R_k <= R_hi <= b keeps the b bounds; every stored-endpoint chord stays in
    [a - g, b] (the norm is convex: its maximum on a chord is at an end). Exit: R in [a - g, a),
    |P| in [p_lo - 2 count K, p_hi + 2 count K], |L| <= L_hi + count dL, w <= min(w_c + gain, the identity at a - g).
    The L term matters: with the accumulated W + n gain alone, P_cap > |P| makes an artificial turning radius
    ~ R0 sqrt(2 (P_cap/|P| - 1)), so no long leg from R_J closes (found while building V1; docs section 3).
Chain: shells from the entry down to A = 20 + g (geometric ratio 4/5, a fixed rule, never fitted to trajectories). The
last exit is the handoff packet R in [20, 20 + g), w < 0 (IN-3): no step whose chord reaches R < 20 is in this proof.

Every inequality is checked in exact rationals; any that does not close is NotCertified (outer_bound_not_certified),
which is not a physics failure. Future rounding decisions are not certified (same scope as the outgoing code). A sampled
trajectory is never a premise: the tests that run the executor only CHECK the packet (docs section 5).
"""
from __future__ import annotations

from fractions import Fraction as Q

from a_reference import c1b1_energy_bound as EB
from a_reference import c1b1_outer_bootstrap as O
from a_reference import c1b1_outer_bound as B
from a_reference import c1b1_two_atom as C

VERSION = "c1b1-inbound-outer-v1"
SHELL_RATIO = Q(4, 5)
R_INNER = Q(20)
MAX_BUDGET_ROUNDS = 64
NotCertified = O.NotCertified


def _floor(x: Q) -> int:
    return x.numerator // x.denominator


def _zero_impulse_leg(run, q, radius):
    """(Z): exact straight lattice line while R >= R_J. Returns the leg record."""
    if run.J_cache is not None and run.J_cache != (0, 0, 0):
        raise NotCertified("nonzero or malformed cache beyond the zero-impulse radius")
    delta, atom_jumps = O._jump(run, run.atoms)
    qd, dd = O._dot(q, delta), O._norm2(delta)
    if dd == 0 or qd >= 0:
        raise NotCertified("zero-impulse stored drift is not strictly inbound")
    n_z = _first_below(dd, 2 * qd, O._norm2(q), radius * radius)            # |q + n delta|^2 < R_J^2, exactly
    if n_z is None:
        raise NotCertified("the zero-impulse lattice line never enters R_J")
    q_z = tuple(x + n_z * d for x, d in zip(q, delta))
    for atom, jump in zip(run.atoms, atom_jumps):                           # linear motion: the end points suffice
        for raw, dx in zip(atom.r, jump):
            end = Q(raw, 1 << 48) + n_z * dx
            if not Q(run.pos.lo, 1 << 48) <= end <= Q(run.pos.hi, 1 << 48):
                raise NotCertified("zero-impulse leg leaves the position profile")
    r_lo = O._sqrt_down(O._norm2(q_z))
    if r_lo < R_INNER:
        raise NotCertified("zero-impulse leg ends below R = 20")
    env = O.ForceEnvelope()
    k_z = B.H * env.value(r_lo) / 2 + O.U
    return {"steps": n_z, "delta": delta, "exit_q": q_z, "exit_radius_lower": r_lo, "last_kick_cap": k_z,
            "atom_jumps": atom_jumps, "executor_potential_change_cap": env.integral(r_lo)}


def _first_below(quad, lin, const, target):
    """Smallest integer n >= 0 with f(n) = quad n^2 + lin n + const < target (quad > 0), or None if no integer n
    gets there. Exact: f falls up to its real vertex, so "f(n) < target" is monotone on [0, the first integer past it]."""
    f = lambda n: quad * n * n + lin * n + const
    if f(0) < target:
        return 0
    vertex = _floor(-lin / (2 * quad)) + 1
    if vertex < 1 or (f(vertex - 1) >= target and f(vertex) >= target):
        return None
    lo, hi = 0, vertex if f(vertex) < target else vertex - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        lo, hi = (mid, hi) if f(mid) >= target else (lo, mid)
    return hi


def _mirror_shell(a, b, entry_hi, p_hi, p_lo, W, L_hi, p_cap, energy=None):
    g = O.ALPHA * p_cap + O.D
    lower = a - g
    if lower < R_INNER:
        raise NotCertified("a chord of this shell could reach R < 20")
    domain = O._covered_shell(lower, b)
    k = B.H * domain.force / 2 + O.U
    step = B.step_budget(domain, p_cap)
    dL = step["angular_bohr_momentum"]["total"]                        # |L_(k+1) - L_k| per step (c1b1_outer_bound)
    gain = 2 * b * k + O.ALPHA * p_cap ** 2 + O.D * p_cap
    c0 = 2 * b * O.D + (O.ALPHA * p_cap + O.D) ** 2
    dE = step["energy_hartree"]["total"]                               # |E~_(k+1) - E~_k| per step (c1b1_outer_bound)
    n, pe = 1, None
    for _ in range(MAX_BUDGET_ROUNDS):
        half_cap, pl = p_hi + 2 * n * k, max(Q(0), p_lo - 2 * n * k)       # kick-accumulated (V1)
        if energy is not None:                                         # energy-based (Energy Bound E2), no accumulation
            pe = EB.momentum_range(energy.widen(n * dE), domain.radial[0], domain.force)
            if pe is None:
                raise NotCertified("energy forbids this shell")
            half_cap, pl = min(half_cap, pe[1] + k), max(pl, pe[0])
        if half_cap > p_cap:
            raise NotCertified("momentum induction budget did not close")
        lh = L_hi + n * dL
        w_ceil = W + n * gain
        x = a * a * pl * pl - lh * lh
        if x > 0:
            w_ceil = min(w_ceil, -O._sqrt_down(x))                     # (q.P)^2 = R^2 |P|^2 - |L|^2, q.P < 0, R >= a
        if w_ceil + gain >= 0:
            raise NotCertified("inbound q.P ceiling did not stay negative")
        hw_ceil = w_ceil + b * k
        g_in = -(2 * O.ALPHA * hw_ceil + c0)
        if g_in <= 0:
            raise NotCertified("strict inward radial induction did not close")
        count = _floor((entry_hi * entry_hi - a * a) / g_in) + 1 if entry_hi >= a else 0
        if count <= n:
            break
        n = count
    else:
        raise NotCertified("mirror induction budget did not close")
    p_lo_x, p_hi_x, L_hi_x = max(Q(0), p_lo - 2 * count * k), p_hi + 2 * count * k, L_hi + count * dL
    if pe is not None:                                                 # the exit state is in the domain, E~ within n dE
        p_lo_x, p_hi_x = max(p_lo_x, pe[0]), min(p_hi_x, pe[1])
    w_exit = w_ceil + gain
    x = lower * lower * p_lo_x * p_lo_x - L_hi_x * L_hi_x
    if x > 0:
        w_exit = min(w_exit, -O._sqrt_down(x))
    return {"a": a, "b": b, "guard_low": lower, "chord_region": (lower, b), "p_cap": p_cap, "induction_budget": n,
            "max_steps": count, "g_in": g_in, "w_ceiling": w_ceil, "half_step_w_ceiling": hw_ceil, "w_gain_per_step": gain,
            "L_change_per_step": dL, "half_kick_cap": k, "force_cap": domain.force,
            "guard_cells": tuple((s.a, s.b) for s in domain.cells),
            "entry_enclosure": {"radius_upper": entry_hi, "p_norm": (p_lo, p_hi), "q_dot_p_upper": W, "L_norm_upper": L_hi},
            "exit_enclosure": {"radius": (lower, a), "p_norm": (p_lo_x, p_hi_x), "q_dot_p_upper": w_exit,
                               "L_norm_upper": L_hi_x},
            "step_budget": step, "energy_step_budget": dE,
            "energy_entry": None if energy is None else (energy.lo, energy.hi),
            "energy_momentum_range": pe,
            **{key: {t: count * v for t, v in step[key].items()} for key in ("energy_hartree", "angular_bohr_momentum")}}


def _handoff_radius(shells, zero, r2, A):
    """The handoff state's radius enclosure, three paths with three meanings (never mixed; 2026-09-30 audit):
      shells run          -> the last shell's exit enclosure [a - g, a) = [20, A);
      zero leg, no shell  -> the zero leg's exact exit position q_e (its last kick does not move it);
      neither             -> the starting stored state itself is the handoff."""
    if shells:
        return shells[-1]["exit_enclosure"]["radius"][0], A
    if zero is not None:
        r2_e = O._norm2(zero["exit_q"])
        return O._sqrt_down(r2_e), B.sqrt_up(r2_e)
    return O._sqrt_down(r2), B.sqrt_up(r2)


def _overflow(start_r, start_p, pos, mom, half_kick_sum, steps):
    """Absolute per-atom, per-component margins over the shell steps (as c1b1_outer_bootstrap._check_overflow, from
    the given absolute start)."""
    pos_limit, mom_limit = Q(pos.hi, 1 << 48), Q(mom.hi, 1 << 80)
    for r_atom, p_atom in zip(start_r, start_p):
        for r0, p0 in zip(r_atom, p_atom):
            pc = abs(p0) + 2 * half_kick_sum
            dx = B.H * pc / C.AR40_MASS_ME + B.UX / 2
            if pc > mom_limit or abs(r0) + steps * dx > pos_limit:
                raise NotCertified("absolute profile overflow margin did not close")


def certify_inbound_outer(run, p_cap, energy=False):
    """Prove that the exact executor map takes this stored outer inbound state to a handoff state with R in [20, 20+g),
    w < 0, within the recorded step bound -- conditional on the future reference rounding decisions."""
    p_cap = B.exact(p_cap)
    if p_cap <= 0:
        raise NotCertified("positive momentum cap required")
    q, p, snapshot = O._state(run)
    r2 = O._norm2(q)
    if r2 < R_INNER * R_INNER:
        raise NotCertified("state is already inside R < 20 (inner)")
    w0 = O._dot(q, p)
    E = EB.energy_of_state(q, p) if energy else None
    if w0 >= 0:
        raise NotCertified("state is not inbound (q.P >= 0)")
    if B.sqrt_up(O._norm2(p)) > p_cap:
        raise NotCertified("momentum cap below the current momentum")
    g = O.ALPHA * p_cap + O.D
    A = R_INNER + g
    radius = O.zero_impulse_radius()
    start_r = [C.exact(run.pos, a.r) for a in run.atoms]
    start_p = [C.exact(run.mom, a.p) for a in run.atoms]
    p_hi, p_lo = B.sqrt_up(O._norm2(p)), O._sqrt_down(O._norm2(p))
    zero = None
    if O._sqrt_down(r2) >= radius:
        zero = _zero_impulse_leg(run, q, radius)
        q_e = zero["exit_q"]
        k_z = zero["last_kick_cap"]
        entry_hi = B.sqrt_up(O._norm2(q_e))
        W = O._dot(q_e, p) + entry_hi * k_z
        L_hi = B.sqrt_up(O._norm2(_cross(q_e, p))) + entry_hi * k_z       # |q_e x J| <= |q_e| |J|
        p_hi, p_lo = p_hi + k_z, max(Q(0), p_lo - k_z)
        if energy:
            E = EB.energy_of_packet(O._sqrt_down(O._norm2(q_e)), entry_hi, p_lo, p_hi)
        start_r = [tuple(x + zero["steps"] * d for x, d in zip(r, C.exact(run.pos, j)))
                   for r, j in zip(start_r, zero["atom_jumps"])]
        kick_sum = k_z / 2                                                  # one half kick, counted in 2 * sum below
    else:
        try:
            j = C.impulse(q, B.H / 2, run.mom)
            if run.J_cache is not None and run.J_cache != j:
                raise NotCertified("initial impulse cache mismatch")
            jump, _ = O._jump(run, C._kick(run.mom, run.atoms, j))
        except C.ReferenceUndecided as error:
            raise NotCertified("initial impulse precision refused") from error
        except C.ExecutorLimitExceeded as error:
            raise NotCertified(f"initial executor limit exceeded: {error}") from error
        if O.radius_squared_increment(q, jump) >= 0:
            raise NotCertified("initial stored drift does not decrease R squared")
        entry_hi, W, kick_sum = B.sqrt_up(r2), w0, Q(0)
        L_hi = B.sqrt_up(O._norm2(_cross(q, p)))
    shells, total = [], 0
    b = entry_hi
    while b > A:
        a = max(A, b * SHELL_RATIO)
        rec = _mirror_shell(a, b, entry_hi, p_hi, p_lo, W, L_hi, p_cap, E)
        shells.append(rec)
        if E is not None:
            E = E.widen(rec["max_steps"] * rec["energy_step_budget"])
        ex = rec["exit_enclosure"]
        p_lo, p_hi = ex["p_norm"]
        W, L_hi = ex["q_dot_p_upper"], ex["L_norm_upper"]
        entry_hi = a
        total += rec["max_steps"]
        kick_sum += rec["max_steps"] * rec["half_kick_cap"]
        b = a
    handoff_lower, handoff_upper = _handoff_radius(shells, zero, r2, A)
    if handoff_lower < R_INNER or W >= 0:
        raise NotCertified("handoff packet is not at R >= 20 with q.P < 0")
    _overflow(start_r, start_p, run.pos, run.mom, kick_sum, total)
    sources = ("position", "momentum_update", "impulse", "discretization", "other_arithmetic")
    finite = {key: {s: sum((r[key][s] for r in shells), Q(0)) for s in sources}
              for key in ("energy_hartree", "angular_bohr_momentum")}
    for key in finite:
        finite[key]["total"] = sum(finite[key].values(), Q(0))
    return {**O.EXECUTION_SCOPE, "version": VERSION, "evidence": "analytic_inbound_outer_mirror_induction",
            "profile": dict(O.PROFILE), "model_fingerprint": B.FINGERPRINT, "initial_state": snapshot,
            "p_cap": p_cap, "handoff_width_g": g,
            "momentum_bounds": "energy_and_kick" if energy else "kick_accumulated",
            "handoff_energy_range": None if E is None else (E.lo, E.hi),
            "zero_impulse_leg": None if zero is None else {
                "R_J": radius, "steps_exact": zero["steps"], "exit_q_exact": zero["exit_q"],
                "last_kick_cap": zero["last_kick_cap"],
                "executor_potential_change_cap_hartree": zero["executor_potential_change_cap"],
                "relative_L_change_before_last_kick_exact": tuple(zero["steps"] * x for x in _cross(zero["delta"], p))},
            "shells": shells, "max_shell_steps": total,
            "handoff_packet": {"radius": (handoff_lower, handoff_upper),
                               "p_norm": (p_lo, p_hi), "q_dot_p_upper": W, "L_norm_upper": L_hi,
                               "J_cache": "the executor's J at the handoff position (decided when reached)"},
            "finite_shell_energy_hartree": finite["energy_hartree"],
            "finite_shell_angular_bohr_momentum": finite["angular_bohr_momentum"],
            "chord_scope": "every certified step's stored-endpoint chord lies in R >= 20",
            "inner": "not_claimed", "global_trajectory_shadowing": "not_claimed",
            "incoming_asymptote": "not_claimed", "attainability": "not_proved"}


def _cross(u, v):
    return (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
