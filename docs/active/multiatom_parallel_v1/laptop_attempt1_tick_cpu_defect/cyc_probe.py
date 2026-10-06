import ctypes, ctypes.wintypes as wt, multiprocessing as mp, sys, time
import psutil

K32 = ctypes.WinDLL("kernel32")
K32.GetCurrentProcess.restype = wt.HANDLE
K32.QueryProcessCycleTime.argtypes = [wt.HANDLE, ctypes.POINTER(ctypes.c_ulonglong)]


def cycles():
    v = ctypes.c_ulonglong()
    K32.QueryProcessCycleTime(K32.GetCurrentProcess(), ctypes.byref(v))
    return v.value


def rate():
    """cycles per second of on-CPU time: busy loop on one pinned thread, cycles / wall."""
    c0, w0 = cycles(), time.perf_counter()
    x = 0
    while time.perf_counter() - w0 < 0.3:
        x += 1
    return (cycles() - c0) / (time.perf_counter() - w0)


def burn(ms):
    t = time.perf_counter()
    x = 0
    while time.perf_counter() - t < ms / 1000:
        x += 1


def worker(conn, cpu):
    psutil.Process().cpu_affinity([cpu])
    busy = 0.0
    while True:
        m = conn.recv()
        if m is None:
            break
        b = time.perf_counter()
        burn(m)
        busy += time.perf_counter() - b
        conn.send(1)
    conn.send({"busy_wall": busy, "process_time": time.process_time(), "cycles": cycles(), "rate": rate()})


if __name__ == "__main__":
    psutil.Process().cpu_affinity([0])
    ctx = mp.get_context("spawn")
    pipes = [ctx.Pipe() for _ in range(3)]
    ps = [ctx.Process(target=worker, args=(b, c)) for (a, b), c in zip(pipes, (1, 2, 3))]
    for p in ps:
        p.start()
    conns = [a for a, b in pipes]
    for _ in range(100):
        for c in conns:
            c.send(20)
        for c in conns:
            c.recv()
    for c in conns:
        c.send(None)
    for c in conns:
        d = c.recv()
        print({k: round(v, 3) if k != "cycles" else v for k, v in d.items()},
              "cycle-seconds", round(d["cycles"] / d["rate"], 3))
    print("main process_time", time.process_time(), "main cycle-s", round(cycles() / rate(), 3))
