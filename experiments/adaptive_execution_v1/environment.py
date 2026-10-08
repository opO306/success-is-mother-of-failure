"""ADAPTIVE_EXECUTION_V1 environment layer (protocol 'environment').

collect() returns the environment record: platform, Python, mpmath and its backend, CPU model, logical / physical CPUs,
SMT, the CPUs this process may use (affinity), a cgroup CPU quota, the physical core of every allowed CPU, the GPU
(nvidia-smi) and nvcc, and the contract hashes. env_id() hashes every field except the volatile ones. A matching env_id
only selects a performance profile; it says nothing about correctness (that is the correctness profile's job).
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GPU_SOURCES = ("experiments/gpu_pair_vector_v1/pv1.cu", "experiments/gpu_force_feasibility_v1/g0.cu",
               "experiments/gpu_force_feasibility_v1/gpu_host.py", "experiments/gpu_pair_vector_v1/pv_host.py",
               "experiments/gpu_force_feasibility_v1/compile_plan.py", "experiments/gpu_long_trajectory_v1/support.py",
               "experiments/gpu_long_trajectory_v1/long.py", "experiments/gpu_one_step_v1/one_step.py",
               "experiments/gpu_short_trajectory_v1/traj.py")
VOLATILE = ("hostname", "collected_at", "loadavg", "notes")


def sha_lf(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _run(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return r.stdout if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def _cpu_model():
    if sys.platform.startswith("linux"):
        try:
            for line in Path("/proc/cpuinfo").read_text().splitlines():
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
        except OSError:
            return None
    if os.name == "nt":
        import winreg
        try:
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            return winreg.QueryValueEx(k, "ProcessorNameString")[0].strip()
        except OSError:
            return None
    return platform.processor() or None


def _allowed_cpus():
    import psutil
    return sorted(psutil.Process().cpu_affinity())


def _cpu_quota():
    """Effective CPUs of a Linux cgroup quota (cpu.max v2, cfs_quota_us / cfs_period_us v1), else None."""
    if not sys.platform.startswith("linux"):
        return None
    try:
        q, per = Path("/sys/fs/cgroup/cpu.max").read_text().split()
        return None if q == "max" else int(q) / int(per)
    except (OSError, ValueError):
        pass
    try:
        q = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read_text())
        per = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read_text())
        return None if q <= 0 else q / per
    except (OSError, ValueError):
        return None


def _core_of_cpu(cpus):
    """{cpu: 'package:core'} for the allowed CPUs."""
    out = {}
    if sys.platform.startswith("linux"):
        for c in cpus:
            base = Path(f"/sys/devices/system/cpu/cpu{c}/topology")
            try:
                out[c] = f"{base.joinpath('physical_package_id').read_text().strip()}:{base.joinpath('core_id').read_text().strip()}"
            except OSError:
                out[c] = None
        return out
    if os.name == "nt":
        from experiments.w5_placement_v1 import topology as TOPO
        for i, core in enumerate(TOPO.cores()):
            for group, members in core["group_cpus"]:
                for cpu in members:
                    if group == 0 and cpu in cpus:
                        out[cpu] = f"0:{i}"
        return {c: out.get(c) for c in cpus}
    return {c: None for c in cpus}


def _gpu():
    smi = shutil.which("nvidia-smi")
    if not smi:
        return None
    txt = _run([smi, "--query-gpu=name,driver_version,memory.total,compute_cap", "--format=csv,noheader"])
    if not txt or not txt.strip():
        return None
    name, driver, mem, cc = [x.strip() for x in txt.strip().splitlines()[0].split(",")]
    return {"name": name, "driver": driver, "memory": mem, "compute_cap": cc, "arch": "sm_" + cc.replace(".", "")}


def _nvcc():
    cand = shutil.which("nvcc") or ("/usr/local/cuda/bin/nvcc" if Path("/usr/local/cuda/bin/nvcc").exists() else None)
    if not cand:
        return None
    txt = _run([cand, "--version"]) or ""
    m = re.search(r"release ([0-9.]+)", txt)
    return m.group(1) if m else None


def contracts(root=ROOT):
    from experiments.experience_start_p_v1.experience import current_contracts
    physics, numeric = current_contracts(root)
    return {"physics": physics, "numeric": numeric,
            "gpu_sources": {f: sha_lf(Path(root) / f) for f in GPU_SOURCES}}


def collect(root=ROOT):
    import mpmath
    import psutil
    cpus = _allowed_cpus()
    cores = _core_of_cpu(cpus)
    phys = psutil.cpu_count(False)
    logical = psutil.cpu_count(True)
    rec = {"platform": sys.platform, "os_release": platform.release(), "python": platform.python_version(),
           "mpmath_version": mpmath.__version__, "mpmath_backend": mpmath.libmp.BACKEND, "cpu_model": _cpu_model(),
           "logical_cpus": logical, "physical_cores": phys, "smt_enabled": bool(phys and logical and logical > phys),
           "allowed_cpus": cpus, "cpu_quota": _cpu_quota(), "core_of_cpu": {str(c): v for c, v in cores.items()},
           "gpu": _gpu(), "nvcc": _nvcc(), "contracts": contracts(root),
           "hostname": platform.node()}
    rec["env_id"] = env_id(rec)
    return rec


def canonical(rec):
    return json.dumps({k: v for k, v in rec.items() if k not in VOLATILE + ("env_id",)}, sort_keys=True,
                      separators=(",", ":"))


def env_id(rec):
    return hashlib.sha256(canonical(rec).encode()).hexdigest()


def cpu_correctness_key(rec):
    c = rec["contracts"]
    return (rec["mpmath_version"], rec["mpmath_backend"], c["physics"], c["numeric"])


def gpu_correctness_key(rec):
    g = rec.get("gpu")
    return (json.dumps(rec["contracts"]["gpu_sources"], sort_keys=True), g["arch"] if g else None,
            rec["mpmath_version"], rec["mpmath_backend"])


if __name__ == "__main__":
    print(json.dumps(collect(), indent=1))
