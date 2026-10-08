"""ADAPTIVE_EXECUTION_V1 selector (protocol 'placement', 'selector').

A pure function of (N, T, p, goal, environment record, correctness profile, performance profile of env_id or None).
It never runs or sees a pass. It changes only HOW a pass runs: backend, worker count, CPU placement, GPU block. The
evaluator, p, P2 and the readout are not its business. Refusals are exceptions with a code.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field

from experiments.adaptive_execution_v1 import environment as ENV
from experiments.adaptive_execution_v1.profiles import CORRECTNESS, median
from experiments.w5_placement_v1.plan import ExecutionPlan

EVALUATOR = "rw:R1+R2"
GOALS = ("WALL_MIN", "CPU_MIN")
PARALLEL_W = (3, 4, 6)
TIE = 0.05


class Refusal(Exception):
    def __init__(self, code, reason):
        super().__init__(f"{code}: {reason}")
        self.code, self.reason = code, reason


@dataclass(frozen=True)
class AdaptivePlan:
    evaluator: str
    p: int
    backend: str                      # CPU_SERIAL | CPU_PARALLEL | GPU_HYBRID
    worker_count: int
    main_cpu: int | None
    worker_cpus: tuple
    placement_id: str
    gpu_profile: str | None
    gpu_block: int | None
    goal: str
    reasons: tuple
    evidence_ids: tuple
    env_id: str
    strategy: str = "ADAPTIVE"
    extra: tuple = field(default_factory=tuple)

    def execution_plan(self):
        """The unchanged W5_PLACEMENT_V1 ExecutionPlan of a CPU pass."""
        if self.backend == "GPU_HYBRID":
            raise ValueError("a GPU plan has no CPU ExecutionPlan")
        return ExecutionPlan(self.evaluator, self.p, self.backend, self.worker_count, self.main_cpu,
                             tuple(self.worker_cpus)).validate()

    def record(self):
        d = asdict(self)
        d["worker_cpus"] = list(self.worker_cpus)
        d["reasons"], d["evidence_ids"], d["extra"] = list(self.reasons), list(self.evidence_ids), list(self.extra)
        return d


# ---------------------------------------------------------------------------
# placement
# ---------------------------------------------------------------------------
def _pid(kind, main, workers, cores):
    return hashlib.sha256(json.dumps([kind, main, list(workers), cores]).encode()).hexdigest()


def distinct_core_cpus(env):
    """Allowed CPUs in ascending order, at most one per physical core (SMT siblings unused)."""
    seen, out = set(), []
    for c in sorted(env["allowed_cpus"]):
        core = env["core_of_cpu"].get(str(c))
        if core is None or core in seen:
            continue
        seen.add(core)
        out.append(c)
    return out


def placements(env):
    """{'SERIAL': (main, (), id), 'W3' / 'W4' / 'W6': (main, workers, id)} for the VALID placements only."""
    cpus = distinct_core_cpus(env)
    quota = env.get("cpu_quota")
    limit = len(cpus) if quota is None else min(len(cpus), int(quota))
    core = lambda c: env["core_of_cpu"][str(c)]   # noqa: E731
    out = {}
    if limit >= 1 and cpus:
        out["SERIAL"] = (cpus[0], (), _pid("SERIAL", cpus[0], (), [core(cpus[0])]))
    for W in PARALLEL_W:
        need = 6 if W == 6 else W + 1
        if limit < need:
            continue
        a = cpus[:need]
        if W == 6:
            main, workers = a[0], tuple(a[1:6]) + (a[0],)            # W5 layout: main shares worker 6's CPU
        else:
            main, workers = a[0], tuple(a[1:W + 1])
        out[f"W{W}"] = (main, workers, _pid(f"W{W}", main, workers, [core(c) for c in (main, *workers)]))
    return out


def gpu_placement_id(env):
    g = env.get("gpu") or {}
    return _pid("GPU", None, (), [g.get("arch"), CORRECTNESS["GPU_V1"]["block"], "unpinned"])


# ---------------------------------------------------------------------------
# eligibility
# ---------------------------------------------------------------------------
def cpu_verified(env):
    c = CORRECTNESS["CPU_E2"]
    return ((env["mpmath_version"], env["mpmath_backend"]) in c["verified_mpmath"]
            and env["contracts"]["physics"] == c["physics"] and env["contracts"]["numeric"] == c["numeric"])


def gpu_eligible(N, T, p, env, gate100_passed):
    """(eligible, [reasons it is not])."""
    g = CORRECTNESS["GPU_V1"]
    why = []
    if not env.get("gpu"):
        why.append("NO_GPU")
    elif env["gpu"]["arch"] not in g["verified_arch"]:
        why.append(f"ARCH_UNVERIFIED:{env['gpu']['arch']}")
    if (env["mpmath_version"], env["mpmath_backend"]) not in g["verified_mpmath"]:
        why.append("MPMATH_UNVERIFIED")
    if dict(env["contracts"]["gpu_sources"]) != dict(g["gpu_sources"]):
        why.append("GPU_SOURCES_CHANGED")
    if p not in g["support_p"]:
        why.append(f"P_UNSUPPORTED:{p}")
    if T not in g["domain_N"]:
        why.append(f"T_OUTSIDE:{T}")
    elif N not in g["domain_N"][T]:
        why.append(f"N_OUTSIDE:{N}@T{T}")
    if T == 100 and not gate100_passed:
        why.append("T100_NOT_CONNECTED")
    return not why, why


def check_request(N, T, env):
    if not cpu_verified(env):
        raise Refusal("REFUSED_UNVERIFIED_ENVIRONMENT", "cpu correctness key not verified")
    c = CORRECTNESS["CPU_E2"]
    if T not in c["T_min_N"] or not (c["T_min_N"][T] <= N <= c["N_max"]):
        raise Refusal("UNSUPPORTED_REQUEST", f"N {N} T {T}")


# ---------------------------------------------------------------------------
# plans
# ---------------------------------------------------------------------------
def _plan(kind, p, goal, env, place, reasons, evidence, strategy):
    if kind == "GPU":
        return AdaptivePlan(EVALUATOR, p, "GPU_HYBRID", 0, None, (), gpu_placement_id(env), "GPU_V1",
                            CORRECTNESS["GPU_V1"]["block"], goal, tuple(reasons), tuple(evidence), env["env_id"],
                            strategy)
    main, workers, pid = place[kind]
    backend = "CPU_SERIAL" if kind == "SERIAL" else "CPU_PARALLEL"
    return AdaptivePlan(EVALUATOR, p, backend, len(workers), main, tuple(workers), pid, None, None, goal,
                        tuple(reasons), tuple(evidence), env["env_id"], strategy)


def select(N, T, p, goal, env, perf, gate100_passed=False):
    if goal not in GOALS:
        raise Refusal("UNSUPPORTED_GOAL", goal)
    check_request(N, T, env)
    place = placements(env)
    if "SERIAL" not in place:
        raise Refusal("NO_VALID_PLACEMENT", "no allowed CPU")
    if goal == "CPU_MIN":
        return _plan("SERIAL", p, goal, env, place, ["SEALED_CPU_MIN_RULE_SERIAL"], [], "ADAPTIVE")
    g_ok, g_why = gpu_eligible(N, T, p, env, gate100_passed)
    base = [] if g_ok else ["GPU_INELIGIBLE:" + ",".join(g_why)]
    if perf is None:
        return _plan("SERIAL", p, goal, env, place, base + ["NO_PERF_PROFILE"], [], "ADAPTIVE")
    if perf.env_id != env["env_id"]:
        raise Refusal("PERF_PROFILE_ENV_MISMATCH", "a profile of another environment")
    if not perf.has_class(N, T):
        return _plan("SERIAL", p, goal, env, place, base + ["PERF_CLASS_UNMEASURED"], [perf.sha256], "ADAPTIVE")
    cands = []
    for kind in ("SERIAL",) + tuple(f"W{w}" for w in PARALLEL_W) + (("GPU",) if g_ok else ()):
        row = perf.row(N, T, kind)
        if row is None:
            continue
        pid = gpu_placement_id(env) if kind == "GPU" else (place[kind][2] if kind in place else None)
        if pid is None or row["placement_id"] != pid or row["env_id"] != env["env_id"]:
            continue
        workers = 0 if kind in ("SERIAL", "GPU") else int(kind[1:])
        cands.append((median(row["wall_s"]), median(row["cpu_s"]), workers, kind, row["row_id"]))
    if not cands:
        return _plan("SERIAL", p, goal, env, place, base + ["NO_USABLE_ROW"], [perf.sha256], "ADAPTIVE")
    best = min(cands)
    tied = [c for c in cands if (c[0] - best[0]) / best[0] <= TIE]
    pick = min(tied, key=lambda c: (c[1], c[2], c[3]))
    reasons = base + [f"WALL_MIN:{pick[3]}", "candidates:" + ";".join(f"{c[3]}={c[0]:.3f}s/{c[1]:.3f}cpu" for c in
                                                                      sorted(cands, key=lambda c: c[3]))]
    if len(tied) > 1:
        reasons.append("TIE:" + ",".join(sorted(c[3] for c in tied)))
    return _plan(pick[3], p, goal, env, place, reasons, [perf.sha256] + [c[4] for c in cands], "ADAPTIVE")


def fixed(kind, N, T, p, env, gate100_passed=False):
    """Baseline plans without the selector: SERIAL, W6, GPU. A GPU baseline outside the profile is refused here."""
    check_request(N, T, env)
    place = placements(env)
    if kind == "GPU":
        ok, why = gpu_eligible(N, T, p, env, gate100_passed)
        if not ok:
            raise Refusal("REFUSED_GPU_OUTSIDE_PROFILE", ",".join(why))
        return _plan("GPU", p, None, env, place, ["FIXED_GPU"], [], "FIXED_GPU")
    if kind not in place:
        raise Refusal("NO_VALID_PLACEMENT", kind)
    return _plan(kind, p, None, env, place, [f"FIXED_{kind}"], [], f"FIXED_{kind}")


def simulated_env(env, case):
    """Environment cases U2 / U3 (protocol 'environment_cases'): the real record with one field replaced and env_id
    recomputed, labelled SIMULATED. U1 needs no change of the record (it only has no profile)."""
    e = json.loads(json.dumps(env))
    if case == "U2_gpu_unverified":
        e["gpu"] = dict(e["gpu"] or {}, arch="sm_75", name="SIMULATED_UNVERIFIED_GPU")
    elif case == "U3_cpu_unverified":
        e["mpmath_backend"] = "gmpy"
    else:
        raise ValueError(case)
    e["notes"] = f"SIMULATED:{case}"
    e["env_id"] = ENV.env_id(e)
    return e
