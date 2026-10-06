"""ExecutionPlan: what to run where (W5_PLACEMENT_V1 protocol 'execution_plan').

A plan names the evaluator, precision, backend, worker count and CPU placement. CPU_SERIAL and CPU_PARALLEL delegate to
the unchanged runners (experiments/multiatom_parallel_v1/run.run_serial, experiments/e2_pair_parallel_v1/run.run_parallel).
GPU is a reserved backend name only: it is validated as a name and refused at execution (no GPU code exists here).
A future selector returns the same structure.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

EVALUATORS = ("algebra", "rw:R1+R2")
BACKENDS = ("CPU_SERIAL", "CPU_PARALLEL", "GPU")
IMPLEMENTED = ("CPU_SERIAL", "CPU_PARALLEL")


@dataclass(frozen=True)
class ExecutionPlan:
    evaluator: str
    precision: int
    backend: str
    worker_count: int
    main_cpu: int
    worker_cpus: tuple = field(default_factory=tuple)

    def validate(self, logical_cpus=None):
        if self.evaluator not in EVALUATORS:
            raise ValueError(f"evaluator {self.evaluator!r}")
        if self.backend not in BACKENDS:
            raise ValueError(f"backend {self.backend!r}")
        if not (isinstance(self.precision, int) and 64 <= self.precision <= 1024):
            raise ValueError(f"precision {self.precision!r}")
        if self.backend == "CPU_SERIAL" and (self.worker_count != 0 or self.worker_cpus):
            raise ValueError("CPU_SERIAL has no workers")
        if self.backend == "CPU_PARALLEL":
            if self.worker_count < 1 or len(self.worker_cpus) != self.worker_count:
                raise ValueError("worker_count must equal len(worker_cpus)")
            if len(set(self.worker_cpus)) != len(self.worker_cpus):
                raise ValueError("a CPU is assigned to two workers")
        cpus = [self.main_cpu, *self.worker_cpus]
        if logical_cpus is not None and any(not 0 <= c < logical_cpus for c in cpus):
            raise ValueError(f"CPU outside 0..{logical_cpus - 1}")
        return self

    def shares_main_core(self):
        return self.main_cpu in self.worker_cpus

    def to_json(self):
        d = asdict(self)
        d["worker_cpus"] = list(self.worker_cpus)
        return json.dumps(d, sort_keys=True)

    @staticmethod
    def from_json(text):
        d = json.loads(text)
        d["worker_cpus"] = tuple(d.get("worker_cpus", ()))
        return ExecutionPlan(**d)


def execute(plan, n, T):
    """Run one FCC_N trajectory of N atoms for T steps under the plan; returns the runner's record."""
    plan.validate()
    if plan.backend not in IMPLEMENTED:
        raise NotImplementedError(f"backend {plan.backend} is reserved and not implemented")
    if plan.backend == "CPU_SERIAL":
        from experiments.multiatom_parallel_v1 import run as MARUN
        return MARUN.run_serial(plan.evaluator, n, T, plan.precision, plan.main_cpu)
    from experiments.e2_pair_parallel_v1 import run as E2RUN
    return E2RUN.run_parallel(plan.evaluator, n, T, plan.precision, plan.worker_count, plan.main_cpu,
                              list(plan.worker_cpus))
