"""Parallel job runner for bench studies that cannot hang on a dead worker.

History:
- S3: the OOM killer took two multiprocessing.Pool workers; Pool replaced them and imap_unordered waited forever for
  the lost results. Long-lived workers had grown to 1.3 GB each (one job in a fresh process: 28-50 MB).
- S3b test run 1: ProcessPoolExecutor(max_tasks_per_child=...) hung with no worker processes left, a documented
  CPython problem (docs note on max_tasks_per_child, gh-115634).
So: one fresh 'spawn' process per job, at most `workers` at a time. A process that exits without delivering its row
is reported (LOST, exit code), the rows that did arrive are kept, and the run ends with exit code 3 (fail closed).
"""
import json
import multiprocessing as mp
import queue
import sys
import time


def _child(fn, job, idx, q):
    q.put((idx, fn(job)))


def run_jobs(fn, jobs, out, workers=4, label='', grace_s=60):
    """fn(job) -> dict row (must not raise; record errors in the row). Rows are appended to `out` as JSONL."""
    ctx = mp.get_context('spawn')
    q = ctx.Queue()
    t0 = time.perf_counter()
    print(f'{label}{len(jobs)} jobs, {workers} workers, one process per job', flush=True)
    pending = list(enumerate(jobs))
    running, exited_at, lost = {}, {}, []
    done = 0
    with open(out, 'a', encoding='utf-8') as f:
        def take(timeout):
            nonlocal done
            try:
                i, row = q.get(timeout=timeout)
            except queue.Empty:
                return False
            f.write(json.dumps(row) + '\n'); f.flush()
            p = running.pop(i); p.join(); exited_at.pop(i, None)
            done += 1
            if done % 20 == 1 or done == len(jobs):
                print(f'{done}/{len(jobs)} {time.perf_counter() - t0:.0f}s', flush=True)
            return True
        while (pending or running) and not lost:
            while pending and len(running) < workers:
                i, j = pending.pop(0)
                p = ctx.Process(target=_child, args=(fn, j, i, q), daemon=True)
                p.start()
                running[i] = p
            take(0.5)
            now = time.perf_counter()
            for i, p in list(running.items()):
                if p.is_alive():
                    continue
                if p.exitcode != 0:                       # died without a row (killed, crashed)
                    lost.append((i, p.exitcode))
                elif now - exited_at.setdefault(i, now) > grace_s:   # clean exit but its row never arrived
                    lost.append((i, 0))
        if lost:
            for p in running.values():
                if p.is_alive():
                    p.terminate()
            while take(1.0):                              # keep rows that did arrive
                pass
            print(f'WORKER_DIED after {done}/{len(jobs)} rows', flush=True)
            for i, code in lost:
                print('LOST', json.dumps(jobs[i]), 'exitcode', code, flush=True)
            for i, _ in pending:
                print('NOT_STARTED', json.dumps(jobs[i]), flush=True)
            sys.exit(3)
    print(f'done {time.perf_counter() - t0:.0f}s', flush=True)
