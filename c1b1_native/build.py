"""Build the native track with g++ (integer code; no fast-math or machine-specific flags).

C3b-1: `src` selects the source (default track.cpp; the sealed C3a copy is reference_c3a/track_c3a.cpp) and
`check=True` adds -DCHECK_INVARIANTS (normal-form check on every operation, plus the 'stats' command).
"""
import hashlib
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / 'track.cpp'
SEALED_C3A = HERE / 'reference_c3a' / 'track_c3a.cpp'
SEALED_C3A_SHA256 = 'e71293f22748f9c7'          # sha256 of the LF-normalised bytes (plan: hash rule)
FLAGS = ['-std=c++17', '-Wall', '-Wextra']
FORBIDDEN = ('-ffast-math', '-Ofast', '-march=native', '-funsafe-math-optimizations', '-ffp-contract=fast')


def lf_sha256(path):
    """sha256 of the file with CRLF turned into LF (Windows checkouts store CRLF; the hashes are defined on LF)."""
    return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def build(opt='-O2', inject=0, out_dir=None, src=None, check=False):
    """Path of the executable for this source, optimisation level, fault-injection number and check flag."""
    if opt not in ('-O0', '-O2'):
        raise ValueError(opt)
    src = Path(src or SRC)
    out_dir = Path(out_dir or Path(tempfile.gettempdir()) / 'c1b1_native_build')
    out_dir.mkdir(parents=True, exist_ok=True)
    sha = lf_sha256(src)[:12]
    exe = out_dir / f'track_{sha}_{opt[1:]}_i{inject}{"_chk" if check else ""}'
    if not exe.exists():
        cmd = ['g++', opt, *FLAGS, f'-DINJECT={int(inject)}', *(['-DCHECK_INVARIANTS'] if check else []),
               '-o', str(exe) + '.tmp', str(src)]
        subprocess.run(cmd, check=True)
        Path(str(exe) + '.tmp').rename(exe)
    return exe
