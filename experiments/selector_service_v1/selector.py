"""Selector V1 (SELECTOR_SERVICE_V1 protocol 'selector_v1'). A pure function of the allowed inputs; it never runs or
sees a pass. Returns an ExecutionPlan or raises UnsupportedSelectorDomain.
"""

from __future__ import annotations

from dataclasses import dataclass

from experiments.w5_placement_v1.plan import ExecutionPlan

EVALUATOR = "rw:R1+R2"
GOALS = ("CPU_MIN", "WALL_MIN")
ALLOWED_INPUTS = ("N", "T", "p", "goal", "topology")
SERIAL_CPU, MAIN_CPU = 1, 0


class UnsupportedSelectorDomain(Exception):
    code = "UNSUPPORTED_SELECTOR_DOMAIN"


@dataclass(frozen=True)
class SelectorInput:
    N: int
    T: int
    p: int
    goal: str
    topology: tuple            # ((logical, physical, smt), ((core, (cpu, ...)), ...)) - hashable, read-only

    def as_record(self):
        (logical, physical, smt), cores = self.topology
        return {"N": self.N, "T": self.T, "p": self.p, "goal": self.goal,
                "topology": {"logical": logical, "physical": physical, "smt": smt,
                             "cores": [[c, list(cpus)] for c, cpus in cores]}}


def topology_input(summary):
    """Reduce a topology.summary() to the selector's read-only topology input."""
    smt = any(c["smt"] for c in summary["cores"])
    cores = tuple((i, tuple(cpu for _, cpus in c["group_cpus"] for cpu in cpus)) for i, c in enumerate(summary["cores"]))
    return ((summary["logical"], summary["physical"], smt), cores)


def _supported_topology(topo):
    (logical, physical, smt), cores = topo
    return logical == 6 and physical == 6 and not smt and cores == tuple((k, (k,)) for k in range(6))


def worker_count(N, T, goal):
    if goal == "CPU_MIN":
        return 0
    if T == 100:
        if N < 2:
            raise UnsupportedSelectorDomain(f"N {N}")
        return 0 if N <= 4 else (4 if N < 12 else 6)
    if T == 1000:
        if N < 3:
            raise UnsupportedSelectorDomain(f"N {N} at T 1000")
        return 3 if N == 3 else 6
    raise UnsupportedSelectorDomain(f"T {T}")


def select(inp: SelectorInput) -> ExecutionPlan:
    if not isinstance(inp, SelectorInput):
        raise TypeError("selector accepts only a SelectorInput")
    if inp.goal not in GOALS:
        raise UnsupportedSelectorDomain(f"goal {inp.goal!r}")
    if inp.T not in (100, 1000):
        raise UnsupportedSelectorDomain(f"T {inp.T}")
    if not _supported_topology(inp.topology):
        raise UnsupportedSelectorDomain("topology")
    w = worker_count(inp.N, inp.T, inp.goal)       # p is an input but V1 does not use it for the worker count
    if w == 0:
        return ExecutionPlan(EVALUATOR, inp.p, "CPU_SERIAL", 0, SERIAL_CPU, ()).validate(logical_cpus=6)
    cpus = tuple(range(1, w + 1)) if w <= 5 else (1, 2, 3, 4, 5, 0)
    return ExecutionPlan(EVALUATOR, inp.p, "CPU_PARALLEL", w, MAIN_CPU, cpus).validate(logical_cpus=6)


def fixed_plan(kind, p):
    """Baseline / shadow plans that do not use the selector: SERIAL, W3, W4, W6."""
    if kind == "GPU":                                    # reserved backend name: a valid plan that must be refused
        return ExecutionPlan(EVALUATOR, p, "GPU", 0, MAIN_CPU, ()).validate()
    if kind == "SERIAL":
        return ExecutionPlan(EVALUATOR, p, "CPU_SERIAL", 0, SERIAL_CPU, ()).validate(logical_cpus=6)
    w = int(kind[1:])
    cpus = tuple(range(1, w + 1)) if w <= 5 else (1, 2, 3, 4, 5, 0)
    return ExecutionPlan(EVALUATOR, p, "CPU_PARALLEL", w, MAIN_CPU, cpus).validate(logical_cpus=6)
