"""Build the C3a native track with g++ (integer code; no fast-math or machine-specific flags)."""
import hashlib
import subprocess
import tempfile
from pathlib import Path

SRC = Path(__file__).resolve().parent / 'track.cpp'
FLAGS = ['-std=c++17', '-Wall', '-Wextra']
FORBIDDEN = ('-ffast-math', '-Ofast', '-march=native', '-funsafe-math-optimizations', '-ffp-contract=fast')


def build(opt='-O2', inject=0, out_dir=None):
    """Path of the executable for this source, optimisation level and fault-injection number (cached by sha)."""
    if opt not in ('-O0', '-O2'):
        raise ValueError(opt)
    out_dir = Path(out_dir or Path(tempfile.gettempdir()) / 'c1b1_native_build')
    out_dir.mkdir(parents=True, exist_ok=True)
    sha = hashlib.sha256(SRC.read_bytes()).hexdigest()[:12]
    exe = out_dir / f'track_{sha}_{opt[1:]}_i{inject}'
    if not exe.exists():
        cmd = ['g++', opt, *FLAGS, f'-DINJECT={int(inject)}', '-o', str(exe) + '.tmp', str(SRC)]
        subprocess.run(cmd, check=True)
        Path(str(exe) + '.tmp').rename(exe)
    return exe
