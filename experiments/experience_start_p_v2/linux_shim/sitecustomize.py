"""EXPERIENCE_START_P_V2 Linux measurement shim (protocol 'platform.cpu_clock_on_linux').

Active only on Linux with ESP2_LINUX_CLOCK=1 (this directory and the repository root on PYTHONPATH). Every Python
process of the job, spawned workers included, imports it at start-up. It replaces exactly two measurement functions of
experiments/multiatom_parallel_v1/run, whose Windows versions (QueryProcessCycleTime, peak working set) do not exist on
Linux:
    cycles() -> CLOCK_PROCESS_CPUTIME_ID of the whole process in nanoseconds (cycle rate is then exactly 1e9)
    _mem()   -> peak resident set size in MB (ru_maxrss)
Nothing else is touched: no physics, numerics, scheduling, readout or result code.
"""
import os
import sys

if sys.platform.startswith("linux") and os.environ.get("ESP2_LINUX_CLOCK") == "1":
    import resource
    import time

    import experiments.multiatom_parallel_v1.run as _M

    def cycles():
        return time.clock_gettime_ns(time.CLOCK_PROCESS_CPUTIME_ID)

    def _mem():
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024

    _M.cycles, _M._mem = cycles, _mem
    _M.CPU_CLOCK = "linux:CLOCK_PROCESS_CPUTIME_ID_ns"
