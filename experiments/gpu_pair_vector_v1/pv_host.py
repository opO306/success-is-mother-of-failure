"""GPU_PAIR_VECTOR_V1 host (GPU side; the checker never imports it): build pv1.cu (+ G0's g0.cu, included verbatim),
upload the G0 program and the stage constants, encode positions, run the kernels, decode, reduce on the host.
"""

from __future__ import annotations

import ctypes
import os
import pathlib
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from fractions import Fraction as Q

from experiments.gpu_force_feasibility_v1 import gpu_host as GH

HERE = pathlib.Path(__file__).resolve().parent
G0_SOURCE = HERE.parent / "gpu_force_feasibility_v1" / "g0.cu"
WORDS_FULL, WORDS_COMPACT, WORDS_ATOM, WORDS_MPI = 114, 68, 26, 22
ST = {0: "PROVEN", 1: "UNPROVEN", 2: "VIOLATED", 3: "REFUSED_DEVICE_WIDTH", 4: "REFUSED_DEVICE_PRECISION"}
BUFFERS = ("pair_table", "status", "mask", "positions", "d", "r2", "G", "J", "full_records", "compact_records",
           "atom_records")
FAULTS = {1: "dx_sign", 2: "dy_other_pair", 3: "dz_missing", 4: "h_times_g_times_d_order", 5: "r2_term_missing",
          6: "domain_removed", 9: "reduce_sign", 10: "reduce_order", 11: "reduce_layout_order"}


@dataclass
class GpuExecutionPlan:
    block_size: int
    grid_blocks: int            # 0 = ceil(work / block) per kernel
    batch_size: int             # pairs per launch (= all pairs of the state)
    pair_storage_mode: str      # DEVICE_PAIR_BUFFER (B1)
    atom_reduction_mode: str    # NONE | CANONICAL_PER_ATOM_COMPONENT
    precision: int


def build(out_dir):
    from a_numeric_native import harness as H
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(G0_SOURCE, out_dir / "g0.cu")
    shutil.copy(HERE / "pv1.cu", out_dir / "pv1.cu")
    nvcc = H.find_nvcc()
    arch = H.device_arch()
    flags = f"-O3 -arch={arch} -std=c++17 -shared -Xptxas -v"
    if os.name == "nt":
        lib = out_dir / "pv1.dll"
        bat = out_dir / "build.bat"
        bat.write_text(f'@call "{H.find_vcvars()}" >nul\r\n@"{nvcc}" {flags} pv1.cu -o pv1.dll\r\n', encoding="mbcs")
        r = subprocess.run(["cmd", "/c", str(bat)], capture_output=True, text=True, cwd=out_dir)
    else:
        lib = out_dir / "libpv1.so"
        r = subprocess.run([str(nvcc), *flags.split(), "-Xcompiler", "-fPIC", "pv1.cu", "-o", "libpv1.so"],
                           capture_output=True, text=True, cwd=out_dir)
    log = (r.stdout or "") + (r.stderr or "")
    (out_dir / "build.log").write_text(log, encoding="utf-8")
    if r.returncode != 0 or not lib.exists():
        raise RuntimeError(f"pv1 build failed:\n{log[-4000:]}")
    return lib, arch, log


def _dn_words(v):
    n = (v.bit_length() + 31) // 32
    return [n] + [(v >> (32 * i)) & 0xffffffff for i in range(n)] + [0] * (GH.DL - n)


class PV(GH.G0):
    def __init__(self, lib_path, device=0):
        super().__init__(lib_path, device)
        L = self.lib
        L.pv_upload_consts.argtypes = [ctypes.POINTER(ctypes.c_uint32)] * 3
        L.pv_alloc.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_ulonglong), ctypes.POINTER(ctypes.c_double)]
        L.pv_run.argtypes = [ctypes.POINTER(ctypes.c_uint32), ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                             ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32),
                             ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_float)]
        L.pv_echo_positions.argtypes = [ctypes.POINTER(ctypes.c_uint32)]
        self.N, self.mem = None, None

    def echo_positions(self):
        buf = (ctypes.c_uint32 * (self.N * 3 * WORDS_MPI))()
        self._ok(self.lib.pv_echo_positions(buf), "pv_echo_positions")
        return buf

    def upload(self, p):
        prog = super().upload(p)                           # G0 program + constants + exp tables at p
        from mpmath import iv

        import exact_expression_gate_v0.lang_iv as LI
        from exact_expression_gate_v1 import common as K
        iv.prec = p
        h = GH.encode_batch([LI.c(K.H)._mpi_])
        a = (ctypes.c_uint32 * (GH.DL + 1))(*_dn_words(Q(K.R_MIN2).numerator))
        b = (ctypes.c_uint32 * (GH.DL + 1))(*_dn_words(Q(K.R_MIN2).denominator))
        self._ok(self.lib.pv_upload_consts(h, a, b), "pv_upload_consts")
        return prog

    def alloc_n(self, N):
        if self.N == N:
            return self.mem
        b = (ctypes.c_ulonglong * 11)()
        ms = ctypes.c_double()
        self._ok(self.lib.pv_alloc(N, b, ctypes.byref(ms)), "pv_alloc")
        self.N = N
        self.mem = {"N": N, "pairs": N * (N - 1) // 2, "bytes": dict(zip(BUFFERS, list(b))), "total_bytes": sum(b),
                    "alloc_ms": ms.value}
        return self.mem

    def run_state(self, pos_buf, N, want, block=128, grid=0, fault=0, g0fault=0, wl=GH.DL):
        self.alloc_n(N)
        P = N * (N - 1) // 2
        full = (ctypes.c_uint32 * (max(P, 1) * WORDS_FULL))() if want & 1 else (ctypes.c_uint32 * 1)()
        comp = (ctypes.c_uint32 * (max(P, 1) * WORDS_COMPACT))() if want & 2 else (ctypes.c_uint32 * 1)()
        atoms = (ctypes.c_uint32 * (N * 3 * WORDS_ATOM))() if want & 4 else (ctypes.c_uint32 * 1)()
        t = (ctypes.c_float * 8)()
        self._ok(self.lib.pv_run(pos_buf, want, block, grid, fault, g0fault, wl, full, comp, atoms, t), "pv_run")
        names = ("h2d_ms", "k_dr2_ms", "k_G_ms", "k_J_ms", "k_reduce_ms", "d2h_full_ms", "d2h_compact_ms", "d2h_atoms_ms")
        return full, comp, atoms, dict(zip(names, list(t)))


def encode_positions(q_ivs):
    """q_ivs: N x 3 raw intervals -> device words (atom-major, component-minor)."""
    return GH.encode_batch([x for row in q_ivs for x in row])


def decode_compact(buf, P):
    out = []
    for pid in range(P):
        o = buf[pid * WORDS_COMPACT:(pid + 1) * WORDS_COMPACT]
        J = tuple((GH._mp_from(o[2 + 22 * k:13 + 22 * k]), GH._mp_from(o[13 + 22 * k:24 + 22 * k])) for k in range(3))
        out.append((ST.get(o[0], o[0]), o[1], J))
    return out


def decode_atoms(buf, N):
    out = []
    for t in range(3 * N):
        o = buf[t * WORDS_ATOM:(t + 1) * WORDS_ATOM]
        out.append((o[0], o[1], o[2], ST.get(o[3], o[3]), (GH._mp_from(o[4:15]), GH._mp_from(o[15:26]))))
    return out


def host_reduce(N, pairs_out, p):
    """CPU canonical reduction of decoded pair impulses (the 'pair vector' path's last step)."""
    from mpmath import iv
    from mpmath.libmp import mpi_add, mpi_sub
    zero = ((0, 0, 0, 0), (0, 0, 0, 0))
    F = [[zero] * 3 for _ in range(N)]
    pid = 0
    for i in range(N):
        for j in range(i + 1, N):
            st, _, J = pairs_out[pid]
            if st != "PROVEN":
                return st, pid, None
            for k in range(3):
                F[j][k] = mpi_add(F[j][k], J[k], p)
                F[i][k] = mpi_sub(F[i][k], J[k], p)
            pid += 1
    return "PROVEN", None, F


def memory_table(Ns=(64, 128, 256, 512, 1024)):
    """Exact bytes the allocation formula of pv_alloc gives for each N (not measured)."""
    rows = []
    for N in Ns:
        P = N * (N - 1) // 2
        b = {"pair_table": P * 8, "status": P * 4, "mask": P * 4, "positions": N * 3 * 88, "d": P * 3 * 88, "r2": P * 88,
             "G": P * 88, "J": P * 3 * 88, "full_records": P * WORDS_FULL * 4, "compact_records": P * WORDS_COMPACT * 4,
             "atom_records": N * 3 * WORDS_ATOM * 4}
        pair_iv = b["d"] + b["r2"] + b["G"] + b["J"]
        rows.append({"N": N, "pairs": P, "pair_interval_buffer_bytes": pair_iv, "atom_output_bytes": b["atom_records"],
                     "scratch_bytes": b["pair_table"] + b["status"] + b["mask"] + b["full_records"] + b["compact_records"],
                     "positions_bytes": b["positions"], "total_gpu_bytes": sum(b.values()),
                     "b2_recompute_bytes_estimate": b["positions"] + b["atom_records"]})
    return rows


def plan_record(block, grid, N, mode, p):
    return asdict(GpuExecutionPlan(block, grid, N * (N - 1) // 2, "DEVICE_PAIR_BUFFER", mode, p))


__all__ = ["PV", "build", "encode_positions", "decode_compact", "decode_atoms", "host_reduce", "memory_table",
           "plan_record", "ST", "time"]
