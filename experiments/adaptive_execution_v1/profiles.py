"""ADAPTIVE_EXECUTION_V1 profiles (protocol 'correctness_profile', 'performance_profile').

CORRECTNESS is the sealed correctness profile: under which conditions an executor's results are known to equal CPU E2.
A performance profile is a sealed file of measured rows for ONE env_id; it says how fast, never whether correct.
Both are read-only; a performance profile is hash-checked at load.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import MappingProxyType

HERE = Path(__file__).resolve().parent
PROFILE_DIR = HERE / "profiles"

# GPU_LONG_TRAJECTORY_V1 docs/active/gpu_long_trajectory_v1/vast_run_3090/env.json 'source_sha256_lf' (LF sha256)
GPU_SOURCES_SEALED = {
    "experiments/gpu_pair_vector_v1/pv1.cu": "840d503768ace8f960ae7550139836878c548d183c249e309a1754365ab583c1",
    "experiments/gpu_force_feasibility_v1/g0.cu": "dc519a9cd3ddc4b2a778cb1497bba324bdedcd8bb3e42b6a4514dc2ee49c21de",
    "experiments/gpu_force_feasibility_v1/gpu_host.py": "dd255cb31b7f07ecb428515b36432f829bed124e75536de89af8a3c201163abe",
    "experiments/gpu_pair_vector_v1/pv_host.py": "bded5b8e8080db947612f0d1101adda766b66157d8bc57a10e6df0da55b376f2",
    "experiments/gpu_force_feasibility_v1/compile_plan.py": "cc63a1e53da6e2c4221b9f7f1d298f987bbe35fdcb46231baa3833a5975ac63b",
    "experiments/gpu_long_trajectory_v1/support.py": "4c58017af84ff0ca630db0179b586986c36edd4a795fd249bbc91b3270477cfb",
    "experiments/gpu_long_trajectory_v1/long.py": "4bf01067a91a8b3972b1a55e37fa0eaa00df2da70a39636a58d5650e4c1e7d94",
    "experiments/gpu_one_step_v1/one_step.py": "cacf8077d8eee6c67d140060fcae467737e97c1c7c4d34c3029738bfde112300",
    "experiments/gpu_short_trajectory_v1/traj.py": "ff4f126e5299189326f5f5590c4d99b4f13ad8310cdb3c13c2c4b3e6ae777eab",
}

CORRECTNESS = MappingProxyType({
    "CPU_E2": MappingProxyType({
        "evaluator": "rw:R1+R2",
        "verified_mpmath": (("1.3.0", "python"),),
        "physics": "5d76fa2ab73bc3139519815c399d3d3e9d782362ab94a9f0cb1227bec460021a",
        "numeric": "85653a0a815e4f1f2d5f548e17545c5cb0cf38bf17ea788c409ab85bc7748f55",
        "T_min_N": MappingProxyType({100: 2, 1000: 3}),
        "N_max": 128,
    }),
    "GPU_V1": MappingProxyType({
        "support_p": (64, 73, 78, 109, 128, 161, 163, 166, 192),
        "verified_arch": ("sm_86", "sm_89"),
        "verified_mpmath": (("1.3.0", "python"),),
        "gpu_sources": MappingProxyType(GPU_SOURCES_SEALED),
        "domain_N": MappingProxyType({1000: (12, 16, 40), 100: (12, 16, 40, 64, 128)}),
        "block": 32,
    }),
})
def plain(x):
    if isinstance(x, (dict, MappingProxyType)):
        return {str(k): plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [plain(v) for v in x]
    return x


CORRECTNESS_ID = hashlib.sha256(json.dumps(plain(CORRECTNESS), sort_keys=True).encode()).hexdigest()


def canonical_bytes(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


class PerfProfile:
    """Read-only performance rows of one env_id. rows: (N, T, strategy) -> row (a copy is returned)."""

    def __init__(self, data, sha256):
        self.sha256 = sha256
        self.env_id = data["env_id"]
        self.gate100_passed = bool(data.get("gate100_passed"))
        self._rows = MappingProxyType({(r["N"], r["T"], r["strategy"]): MappingProxyType(r) for r in data["rows"]})

    def row(self, N, T, strategy):
        r = self._rows.get((N, T, strategy))
        return dict(r) if r is not None else None

    def has_class(self, N, T):
        return any(k[:2] == (N, T) for k in self._rows)


def load_perf(path, expected_sha256=None):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    got = hashlib.sha256(canonical_bytes(raw)).hexdigest()
    sealed = expected_sha256 or Path(str(path) + ".sha256").read_text(encoding="utf-8").split()[0]
    if got != sealed:
        raise ValueError(f"performance profile hash {got} != sealed {sealed}")
    return PerfProfile(raw, got)


def find_perf(env_id, directory=PROFILE_DIR):
    """The sealed profile of this env_id, or None (never a profile of another env_id)."""
    p = Path(directory) / f"perf_{env_id[:16]}.json"
    if not p.exists():
        return None
    prof = load_perf(p)
    if prof.env_id != env_id:
        raise ValueError("performance profile file name / env_id mismatch")
    return prof


def median(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
