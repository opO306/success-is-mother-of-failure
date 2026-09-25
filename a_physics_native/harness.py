"""Build the native C1-A Ar-Ar evaluators (B0 serial, B1 parallel, B2 CUDA) and query them.

The Python reference evaluator (a_reference/ar2_lang2024.py) and its Git fixture are the judges. A native
evaluator receives only (quantity, retardation, profile, raw R) -- never an expected value -- and answers
`ok <raw> <M>`, `domain physics_domain_exceeded`, `halt overflow` or `refuse <reason>`.
"""
from __future__ import annotations

import pathlib
import subprocess
import tempfile

from a_numeric_native.harness import NVCC_FLAGS, find_nvcc, find_vcvars

HERE = pathlib.Path(__file__).resolve().parent
CORE = [HERE / "ar2_core.hpp", HERE.parent / "a_numeric_native" / "anvm_core.hpp"]
SOURCES = {"b0": HERE / "ar2_b0.cpp", "b1": HERE / "ar2_b1.cpp"}
B0_R_MAX_BOHR = 1 << 20


def build(kind: str, out_dir, inject: int = 0, defines: dict | None = None) -> pathlib.Path:
    """Compile an evaluator (MSVC /fp:strict; B2 with nvcc). inject > 0 compiles a deliberate defect."""
    vcvars = find_vcvars()
    if vcvars is None:
        raise RuntimeError("MSVC not found (vswhere/vcvars64.bat)")
    extra = "".join(f"_{k}{v}" for k, v in sorted((defines or {}).items()))
    out = pathlib.Path(out_dir) / f"ar2_{kind}_inject{inject}{extra}"
    dflags = "".join(f" -D{k}={v}" for k, v in sorted((defines or {}).items()))
    out.mkdir(parents=True, exist_ok=True)
    src = HERE / "ar2_b2.cu" if kind == "b2" else SOURCES[kind]
    for f in [src, *CORE]:        # the repository path is not ASCII: compile copies inside out_dir
        (out / f.name).write_bytes(f.read_bytes())
    exe = out / f"ar2_{kind}.exe"
    if kind == "b2":
        nvcc = find_nvcc()
        if nvcc is None:
            raise RuntimeError("nvcc not found")
        cmd = (f'@"{nvcc}" {NVCC_FLAGS} -Xcompiler "/fp:strict /EHsc /wd4702" -DINJECT={inject}{dflags} '
               f'{src.name} -o {exe.name}')
    else:
        cmd = f'@cl /nologo /O2 /fp:strict /EHsc /std:c++17 /W3 /wd4702 /DINJECT={inject}{dflags} {src.name} /Fe{exe.name}'
    bat = out / "build.bat"
    bat.write_text(f'@call "{vcvars}" >nul\r\n{cmd}\r\n', encoding="mbcs")
    r = subprocess.run(["cmd", "/c", str(bat)], capture_output=True, text=True, cwd=out)
    if r.returncode != 0 or not exe.exists():
        raise RuntimeError(f"{kind} build failed:\n{r.stdout[-4000:]}\n{r.stderr[-4000:]}")
    return exe


def profile_token(profile: str) -> str:
    return {"B64": "B64", "FX64_32": "FX:64:32"}[profile]


def encode(queries) -> str:
    """queries: (quantity 'V'|'F', retardation bool, profile 'B64'|'FX64_32', raw str)"""
    return "".join(f"{q} {int(ret)} {profile_token(p)} {raw}\n" for q, ret, p, raw in queries)


def parse(line: str) -> dict:
    w = line.split()
    if w[0] == "ok":
        return {"raw": w[1], "M": int(w[2])}
    if w[0] == "domain":
        return {"domain": w[1]}
    if w[0] == "halt":
        return {"halt": w[1]}
    if w[0] == "refuse":
        return {"refuse": w[1]}
    raise ValueError(line)


def run(exe, queries, args=()) -> list[dict]:
    with tempfile.TemporaryDirectory() as d:
        src, dst = pathlib.Path(d) / "q.txt", pathlib.Path(d) / "a.txt"
        src.write_text(encode(queries), encoding="ascii")
        r = subprocess.run([str(exe), *map(str, args), str(src), str(dst)], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"{exe} exited {r.returncode}: {r.stderr}")
        out = [parse(l) for l in dst.read_text(encoding="ascii").splitlines() if l.strip()]
    assert len(out) == len(queries)
    return out


def as_outcome(ans: dict) -> dict:
    """The answer in the fixture's outcome form (precision M dropped)."""
    return {k: v for k, v in ans.items() if k != "M"}
