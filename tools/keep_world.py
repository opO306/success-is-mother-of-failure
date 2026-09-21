"""Keep primal worlds running unattended, e.g. overnight.

run_primal.py --forever already goes on to the next seed when a world dies out. What it cannot do alone is outlive its
model server: when the server stays silent it stops (a day lived without minds is not data) and waits for a person.
This waits instead, until the server answers again, then goes on from the last whole day. A run that keeps stopping
within minutes is a bug, not an outage: after five of those in a row this stops too and says so.

    python tools/keep_world.py --seed 6 --talent pair [other run_primal.py options]

A world that stops before its first whole day starts over from its seed; under --talent pair that reruns both halves.
Stopping this process does not stop the run_primal.py it started.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import run_primal  # noqa: E402
from engine.primal.config import PrimalConfig  # noqa: E402

QUICK = 600
GIVE_UP_AFTER = 5


def log(text: str) -> None:
    print(f"[keep_world {datetime.now():%m-%d %H:%M:%S}] {text}", flush=True)


def server_up() -> bool:
    try:
        run_primal.check_servers(PrimalConfig().llm)
        return True
    except SystemExit:
        return False


def newest_run(since: float) -> Path | None:
    runs = [p for p in (ROOT / "runs").glob("*_primal_seed*") if p.is_dir() and p.stat().st_ctime >= since - 1]
    return max(runs, key=lambda p: p.stat().st_ctime, default=None)


def where_to_go_on(run: Path) -> tuple[int, str | None]:
    meta = json.loads((run / "meta.jsonl").read_text(encoding="utf-8").splitlines()[0])
    snapshots = sorted((run / "snapshots").glob("day_*.pkl"))
    return meta["seed"], str(snapshots[-1]) if snapshots else meta.get("resume")


def mark(run: Path, code: int, resume: str | None) -> None:
    """run_primal marks a stop for a silent server itself; anything else that stopped it is marked here."""
    if (run / "aborted.jsonl").exists():
        return
    with (run / "aborted.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"reason": f"process exited with code {code}", "resume_from": resume}, ensure_ascii=False) + "\n")
    with (run / "digest.md").open("a", encoding="utf-8") as f:
        f.write("## 실행이 도중에 멈춤 (이 날의 기록은 온전하지 않다)\n\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--talent", choices=["on", "off", "pair"], default="on")
    parser.add_argument("--resume", default=None)
    args, extra = parser.parse_known_args()
    seed, resume, quick_stops = args.seed, args.resume, 0
    while True:
        if not server_up():
            log("모델 서버가 응답하지 않는다. 1분마다 다시 본다")
            while not server_up():
                time.sleep(60)
            log("서버가 다시 응답한다")
        started = time.time()
        cmd = [sys.executable, "-u", "run_primal.py", "--days", "0", "--forever", "--seed", str(seed), "--talent", args.talent, *extra]
        cmd += ["--resume", resume] if resume else []
        log("시작: " + " ".join(cmd[2:]))
        code = subprocess.call(cmd, cwd=ROOT)
        lasted = time.time() - started
        log(f"멈춤: 코드 {code}, {lasted / 60:.0f}분 돌았다")
        run = newest_run(started)
        if run is not None:
            seed, resume = where_to_go_on(run)
            if code != 0:
                mark(run, code, resume)
        quick_stops = quick_stops + 1 if lasted < QUICK else 0
        if quick_stops >= GIVE_UP_AFTER:
            log(f"{QUICK // 60}분도 못 가고 {GIVE_UP_AFTER}번 연달아 멈췄다. 서버가 아니라 코드 문제로 보여 여기서 그만둔다")
            sys.exit(1)
        time.sleep(30)


if __name__ == "__main__":
    main()
