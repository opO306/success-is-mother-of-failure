"""Hard timeout on every native execution (designer verdict 2026-09-27, after an unexplained CUDA hang that ran silently
for an hour): over the limit -> the process AND its children are killed -> the caller fails with NativeTimeout naming
the command, elapsed time, stdout / stderr tails and the profiles. Classified as an execution-infrastructure failure,
never skip, xfail or automatic retry. A stand-in "executor" (the Python interpreter) plays a hung native binary, so these
tests need no compiler and never skip."""
from __future__ import annotations

import sys
import time

import pytest

from a_numeric import FixedPoint
from a_numeric_native import harness as H
from a_physics_native import harness as P

HANG = "import sys, time; print('started', flush=True); print('warming', file=sys.stderr, flush=True); time.sleep(120)"
# a hung executor that also started a child which keeps writing a heartbeat file
HANG_WITH_CHILD = (
    "import subprocess, sys, time\n"
    "beat = sys.argv[1]\n"
    "subprocess.Popen([sys.executable, '-c', 'import sys, time\\nwhile True:\\n    open(sys.argv[1], \"a\").write(\"x\")\\n"
    "    time.sleep(0.05)', beat])\n"
    "time.sleep(120)\n")


def test_the_limit_is_ten_minutes() -> None:
    assert H.NATIVE_TIMEOUT_S == 600


def test_a_hung_native_run_is_killed_and_fails_with_diagnostics() -> None:
    progs = [(FixedPoint(64, 32), {}, [])]
    t0 = time.monotonic()
    with pytest.raises(H.NativeTimeout) as exc:
        H.run_native(sys.executable, progs, ("-c", HANG), timeout=2)
    assert time.monotonic() - t0 < 60                             # killed, not waited out
    msg = str(exc.value)
    assert "2 s hard timeout" in msg and "after" in msg and "infrastructure failure, not physics" in msg
    assert sys.executable in msg and "FX(64,32)" in msg          # command and profile
    assert "started" in msg and "warming" in msg                  # stdout / stderr tails
    assert exc.value.reason == "execution_infrastructure_timeout"
    assert not isinstance(exc.value, (H.NativeRejected, RuntimeError))   # not a capability refusal, not a crash


def test_the_whole_process_tree_is_killed(tmp_path) -> None:
    beat = tmp_path / "beat.txt"
    with pytest.raises(H.NativeTimeout):
        H.run_with_timeout([sys.executable, "-c", HANG_WITH_CHILD, beat], timeout=3)
    time.sleep(1.0)                                               # let a surviving child show itself
    size = beat.stat().st_size
    assert size > 0                                               # the child really ran
    time.sleep(1.0)
    assert beat.stat().st_size == size                            # ... and is dead: the heartbeat stopped


def test_physics_native_runs_share_the_same_timeout() -> None:
    with pytest.raises(H.NativeTimeout) as exc:
        P.run(sys.executable, [("V", True, "FX64_32", "0")], ("-c", HANG), timeout=2)
    assert "FX64_32" in str(exc.value)


def test_a_fast_run_is_untouched() -> None:
    r = H.run_with_timeout([sys.executable, "-c", "print('ok')"], timeout=60)
    assert r.returncode == 0 and r.stdout.strip() == "ok"
