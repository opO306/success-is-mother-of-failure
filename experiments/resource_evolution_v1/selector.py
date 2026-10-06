"""Plans, tiers, selectors and the Rescorla-Wagner cue learner of RESOURCE_EVOLUTION_PILOT_V1 (protocol.json).

A selector sees only the visible environment, cue ids and its own V table; it returns a plan name. It never sees the
request's minimum p, outcomes of the current trial, verifier results or the future schedule.
"""

from __future__ import annotations

import json
import math
from fractions import Fraction as Q
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PARAMS = ROOT / "experiments/precision_pilot_a2t/frozen_policy_params_a1.json"
PHYS_ORDER = [2, 4, 6, 8, 10, 0]
ORCH_CPU = 1
SCEN = ("A2_bound", "A3_low", "A3_high")
TRAIN = [(s, T) for s in SCEN for T in (200, 2000)]
EVAL = [(s, T) for T in (100, 1000, 3000) for s in SCEN]
COND = [("A2_bound", 1000), ("A3_low", 1000), ("A3_high", 1000), ("A2_bound", 3000), ("A3_low", 3000),
        ("A3_high", 3000)]
E1, E2, E0 = "algebra", "rw:R1+R2", "original"

PLANS = {
    "BASE": {"workers": [(E1, 8)], "spec": False},
    "CONS": {"workers": [(E1, 24)], "spec": False},
    "AGG1": {"workers": [(E2, -16)], "spec": False},
    "AGG3": {"workers": [(E2, -16), (E2, 0), (E2, 16)], "spec": True},
    "SPEC_EVAL": {"workers": [(E1, 8), (E2, 8)], "spec": True},
    "SPEC_P_E1": {"workers": [(E1, -16), (E1, 0), (E1, 16)], "spec": True},
    "BASE_E2": {"workers": [(E2, 8)], "spec": False},
}
TIERS = {
    "H0": {"cores": 6, "cpu_u": 50, "wall_fixed": 600.0, "ram_mb": 4096, "spec": 3},
    "H1": {"cores": 4, "cpu_u": 6, "wall_fixed": None, "ram_mb": 2048, "spec": 3},
    "H2": {"cores": 2, "cpu_u": 3, "wall_fixed": None, "ram_mb": 1024, "spec": 2},
    "H3": {"cores": 1, "cpu_u": 1.5, "wall_fixed": None, "ram_mb": 512, "spec": 1},
    "H4": {"cores": 1, "cpu_u": 0.7, "wall_fixed": None, "ram_mb": 256, "spec": 1},
}
RAM_PER_WORKER_MB = 150
ALLOWED_SELECTOR_INPUTS = {"visible_env", "cues", "V"}


def line(s, T):
    prm = json.loads(PARAMS.read_text(encoding="utf-8"))
    a, b = (Q(x) for x in prm["lines"][s])
    return math.ceil(a + b * T)


def start_ps(plan, s, T):
    L = line(s, T)
    return [(ev, max(64, min(1024, L + off))) for ev, off in PLANS[plan]["workers"]]


def env_for(tier, u):
    """Actual budgets of a tier for a request with pass-equivalent u (CPU seconds)."""
    t = TIERS[tier]
    cpu = t["cpu_u"] * u
    wall = t["wall_fixed"] if t["wall_fixed"] is not None else cpu + 5.0
    return {"tier": tier, "cores": t["cores"], "cpu_s": cpu, "wall_s": wall, "ram_mb": t["ram_mb"], "spec": t["spec"],
            "core_set": PHYS_ORDER[:t["cores"]], "u": u}


def visible(env):
    return {"cores": env["cores"], "cpu_u": env["cpu_s"] / env["u"], "spec": env["spec"], "ram_mb": env["ram_mb"]}


def adaptive(vis):
    if vis["cores"] >= 3 and vis["cpu_u"] >= 4 and vis["spec"] >= 3:
        return "AGG3"
    if vis["cpu_u"] >= 2:
        return "BASE"
    return "CONS"


class RW:
    """Rescorla-Wagner associative strengths per cue; alpha 0.3; threshold 0.5."""
    ALPHA, THRESHOLD = 0.3, 0.5

    def __init__(self):
        self.V = {}

    def choose(self, vis, cues):
        inputs = {"visible_env": dict(vis), "cues": list(cues), "V": dict(self.V)}
        if any(self.V.get(c, 0.0) > self.THRESHOLD for c in cues):
            return "CONS", inputs
        return adaptive(vis), inputs

    def update(self, cues, pressure):
        lam = 1.0 if pressure else 0.0
        for c in cues:
            v = self.V.get(c, 0.0)
            self.V[c] = v + self.ALPHA * (lam - v)


def schedule(phase):
    """Conditioning schedules: list of (cues, hidden_pressure)."""
    A, Ap, B, Bp, N = (["A"], False), (["A"], True), (["B"], False), (["B"], True), ([], False)
    if phase == "T5":
        return [A, N, A, A, N, A, A, N, A, A, N, A]
    if phase == "T6":
        return [Ap, N, Ap, Ap, N, Ap, Ap, N, Ap, Ap, N, Ap, Ap, N, Ap, Ap] + [A, A, A, A]
    if phase == "T7A":
        return [A] * 12
    if phase == "T7B":
        return [Bp, A] * 8
    raise ValueError(phase)
