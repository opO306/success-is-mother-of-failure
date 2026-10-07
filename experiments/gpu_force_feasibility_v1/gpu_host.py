"""G0 GPU host (protocol 'gpu_design'): build the CUDA library, upload the traced program and constants for one p,
encode R^2 intervals exactly into 32-bit limbs, run, decode. The checker never imports this module.
"""

from __future__ import annotations

import ctypes
import os
import pathlib
import shutil
import subprocess
import time

from experiments.gpu_force_feasibility_v1 import compile_plan as CP

HERE = pathlib.Path(__file__).resolve().parent
SOURCE = HERE / "g0.cu"
SUPPORTED_P = (64, 109, 128, 163, 192)
ML, DL, NMAG, MAG_LO, NREG = 6, 16, 23, 2, 16
WORDS_MP, WORDS_MPI, WORDS_OUT = 11, 22, 48
STATUS = {0: "OK", 1: "DOMAIN_UNPROVEN", 2: "REFUSED_DEVICE_WIDTH", 3: "REFUSED_DEVICE_PRECISION"}
FAULTS = {0: "none", 1: "lower_inward_mul", 2: "upper_inward_add", 3: "carry_drop", 4: "high_limb_drop",
          5: "exp_no_guard_bits", 6: "sqrt_floor_upper", 7: "den_obligation_removed", 8: "overflow_ignored",
          10: "block64_branch"}
M64 = (1 << 64) - 1


class Refused(Exception):
    pass


def build(out_dir):
    """nvcc -shared with MSVC (Windows) or g++ (Linux); the source is copied (the repository path is not ASCII)."""
    from a_numeric_native import harness as H
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(SOURCE, out_dir / "g0.cu")
    nvcc = H.find_nvcc()
    if nvcc is None:
        raise RuntimeError("nvcc not found")
    arch = H.device_arch()
    flags = f"-O3 -arch={arch} -std=c++17 -shared -Xptxas -v"
    if os.name == "nt":
        lib = out_dir / "g0.dll"
        bat = out_dir / "build.bat"
        bat.write_text(f'@call "{H.find_vcvars()}" >nul\r\n@"{nvcc}" {flags} g0.cu -o g0.dll\r\n', encoding="mbcs")
        r = subprocess.run(["cmd", "/c", str(bat)], capture_output=True, text=True, cwd=out_dir)
    else:
        lib = out_dir / "libg0.so"
        r = subprocess.run([str(nvcc), *flags.split(), "-Xcompiler", "-fPIC", "g0.cu", "-o", "libg0.so"],
                           capture_output=True, text=True, cwd=out_dir)
    log = (r.stdout or "") + (r.stderr or "")
    (out_dir / "build.log").write_text(log, encoding="utf-8")
    if r.returncode != 0 or not lib.exists():
        raise RuntimeError(f"g0 build failed:\n{log[-4000:]}")
    return lib, arch, log


def _mp_words(x):
    sign, man, exp, bc = x
    if bc > ML * 32:
        raise Refused("REFUSED_DEVICE_WIDTH: mantissa wider than the device format")
    n = (bc + 31) // 32
    e = exp & M64
    limbs = man.to_bytes(ML * 4, "little")
    return [sign, n, bc, e & 0xffffffff, e >> 32] + [int.from_bytes(limbs[4 * i:4 * i + 4], "little") for i in range(ML)]


def encode_batch(ivs):
    """Raw intervals -> little-endian uint32 buffer (22 words each)."""
    buf = (ctypes.c_uint32 * (len(ivs) * WORDS_MPI))()
    k = 0
    for a, b in ivs:
        for w in _mp_words(a) + _mp_words(b):
            buf[k] = w
            k += 1
    return buf


def _mp_from(ws):
    sign, n, bc, lo, hi = ws[0], ws[1], ws[2], ws[3], ws[4]
    if n == 0:
        return (0, 0, 0, 0)
    e = (hi << 32) | lo
    if e >> 63:
        e -= 1 << 64
    man = 0
    for i in range(n - 1, -1, -1):
        man = (man << 32) | ws[5 + i]
    return (sign, man, e, bc)


def decode_batch(buf, n):
    """uint32 output buffer -> list of (status, echoed index, obligation mask, G raw interval | None, input echo)."""
    out = []
    for i in range(n):
        o = buf[i * WORDS_OUT:(i + 1) * WORDS_OUT]
        st = STATUS.get(o[0], f"STATUS_{o[0]}")
        g = (_mp_from(o[4:15]), _mp_from(o[15:26])) if o[0] == 0 else None
        echo = (_mp_from(o[26:37]), _mp_from(o[37:48]))
        out.append((st, o[1], o[2], g, echo))
    return out


class G0:
    def __init__(self, lib_path, device=0):
        self.lib = ctypes.CDLL(str(lib_path))
        L = self.lib
        L.g0_init.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_double)]
        L.g0_alloc.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_double)]
        L.g0_upload.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int),
                                ctypes.c_int, ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32),
                                ctypes.POINTER(ctypes.c_double)]
        L.g0_eval.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32),
                              ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_float)]
        L.g0_device_name.argtypes = [ctypes.c_char_p, ctypes.c_int]
        ms = ctypes.c_double()
        self._ok(L.g0_init(device, ctypes.byref(ms)), "init")
        self.setup = {"context_ms": ms.value}
        name = ctypes.create_string_buffer(256)
        L.g0_device_name(name, 256)
        self.device = name.value.decode()
        self.cap, self.p, self.prog = 0, None, None

    @staticmethod
    def _ok(rc, what):
        if rc != 0:
            raise RuntimeError(f"g0_{what} failed with code {rc}")

    def alloc(self, cap):
        ms = ctypes.c_double()
        self._ok(self.lib.g0_alloc(cap, ctypes.byref(ms)), "alloc")
        self.cap = cap
        self.setup["alloc_ms"] = ms.value

    def upload(self, p):
        """Trace the frozen RwForce at p and upload program + constants + exp tables ('model upload')."""
        if p not in SUPPORTED_P:
            raise Refused(f"REFUSED_DEVICE_PRECISION: p {p} not supported")
        t0 = time.perf_counter()
        prog = CP.allocate(CP.trace(p))
        if prog["n_regs"] > NREG:
            raise Refused("REFUSED_DEVICE_WIDTH: too many live registers")
        tab = CP.exp_tables(p, range(MAG_LO, MAG_LO + NMAG))
        code = (ctypes.c_int * (4 * len(prog["code"])))(*[x for op in prog["code"] for x in op])
        consts = encode_batch(prog["consts"])
        ln2 = (ctypes.c_uint32 * (NMAG * (DL + 1)))()
        for k, mag in enumerate(range(MAG_LO, MAG_LO + NMAG)):
            v = tab["ln2"][mag]
            n = (v.bit_length() + 31) // 32
            if n > DL:
                raise Refused("REFUSED_DEVICE_WIDTH: ln2 constant")
            ln2[k * (DL + 1)] = n
            for i in range(n):
                ln2[k * (DL + 1) + 1 + i] = (v >> (32 * i)) & 0xffffffff
        host_ms = (time.perf_counter() - t0) * 1000
        ms = ctypes.c_double()
        self._ok(self.lib.g0_upload(p, tab["wp"], tab["r"], len(prog["code"]), code, len(prog["consts"]), consts, ln2,
                                    ctypes.byref(ms)), "upload")
        self.p, self.prog = p, prog
        self.setup.update(model_trace_ms=host_ms, model_upload_ms=ms.value, n_ops=len(prog["code"]),
                          n_consts=len(prog["consts"]), n_regs=prog["n_regs"])
        return prog

    def run_encoded(self, buf, n, block=128, grid=0, fault=0, wl=DL):
        if n > self.cap:
            self.alloc(n)
        out = (ctypes.c_uint32 * (n * WORDS_OUT))()
        t = (ctypes.c_float * 3)()
        self._ok(self.lib.g0_eval(n, buf, out, block, grid, fault, wl, t), "eval")
        return out, {"h2d_ms": t[0], "kernel_ms": t[1], "d2h_ms": t[2]}

    def evaluate(self, ivs, block=128, grid=0, fault=0, wl=DL):
        """Raw R^2 intervals -> decoded results and a timing breakdown (encode / H2D / kernel / D2H / decode)."""
        t0 = time.perf_counter()
        buf = encode_batch(ivs)
        t1 = time.perf_counter()
        out, tm = self.run_encoded(buf, len(ivs), block, grid, fault, wl)
        t2 = time.perf_counter()
        res = decode_batch(out, len(ivs))
        t3 = time.perf_counter()
        tm.update(encode_ms=(t1 - t0) * 1000, device_call_ms=(t2 - t1) * 1000, decode_ms=(t3 - t2) * 1000,
                  total_ms=(t3 - t0) * 1000)
        return res, tm, out
