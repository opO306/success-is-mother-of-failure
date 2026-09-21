from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

RUNS_ROOT = Path("runs")


def _plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.name
    if is_dataclass(value) and not isinstance(value, type):
        return {k: _plain(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_plain(v) for v in value]
    return value


class RunRecorder:
    """Writes everything a run produces to disk, including the parts that look
    like garbage at the time.

    Failed LLM calls, rejected outputs, discarded discussion rounds and the
    exact prompt text behind every decision are kept deliberately: they are the
    only record of *why* a run went the way it did, and they are the corpus any
    later fine-tuning would have to be built from. A run that keeps only its
    final report has thrown away the evidence and kept the conclusion."""

    def __init__(self, root: Path, meta: dict[str, Any]) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._handles: dict[str, Any] = {}
        self._lock = threading.Lock()  # LLM calls run concurrently and all record here
        self.write("meta", {"started_at": datetime.now().isoformat(), **_plain(meta)})

    def write(self, stream: str, payload: dict[str, Any]) -> None:
        line = json.dumps(_plain(payload), ensure_ascii=False) + "\n"
        with self._lock:
            handle = self._handles.get(stream)
            if handle is None:
                handle = (self.root / f"{stream}.jsonl").open("a", encoding="utf-8")
                self._handles[stream] = handle
            handle.write(line)
            handle.flush()  # a long run that crashes must still leave its data behind

    def record_llm_call(
        self, *, label: str, schema: str, prompt: str, temperature: float | None,
        attempt: int, ok: bool, raw: str | None, parsed: Any, error: str | None,
        latency_s: float, usage: dict[str, Any] | None = None,
    ) -> None:
        self.write("llm_calls", {
            "t": time.time(), "label": label, "schema": schema, "prompt": prompt,
            "temperature": temperature, "attempt": attempt, "ok": ok,
            "raw_response": raw, "parsed": parsed, "error": error,
            "latency_s": round(latency_s, 3), "usage": usage,
        })

    def record_meeting(
        self, *, tick_index: int, company: str, action_description: str,
        roster: list[str], all_rounds: list[list[Any]],
    ) -> None:
        """Every round, not just the binding one -- the rounds where someone
        changed their mind are the interesting ones and were previously
        overwritten each tick."""
        self.write("meetings", {
            "tick": tick_index, "company": company, "action": action_description,
            "roster": roster,
            "rounds": [
                [
                    None if r is None else {
                        "member": roster[i] if i < len(roster) else None,
                        **_plain(r.model_dump()),
                    }
                    for i, r in enumerate(round_responses)
                ]
                for round_responses in all_rounds
            ],
        })

    def record_tick(self, *, tick_index: int, world: Any, tick: Any) -> None:
        self.write("ticks", {
            "world": getattr(world, "label", ""),
            "tick": tick_index,
            "companies": [
                {
                    "name": c.name, "archetype": c.archetype, "alive": c.alive,
                    "isolated": c.isolated, "decision_mode": c.decision_mode,
                    "spawned_from": c.spawned_from,
                    "resources": _plain(c.resources),
                    "employees": [
                        {
                            "name": e.name, "wage": e.wage, "savings": e.savings,
                            "last_wage_paid": e.last_wage_paid, "unpaid_streak": e.unpaid_streak,
                            "temperature": e.temperature, "memory_len": len(e.memory),
                        }
                        for e in c.employees
                    ],
                }
                for c in world.companies
            ],
            "vigilantes": [
                {
                    "name": v.name, "faction": v.faction, "disposition": v.disposition,
                    "grudge_target": v.grudge_target, "capital": v.resources.capital,
                    "temperature": v.temperature, "memory_len": len(v.memory),
                }
                for v in world.vigilantes
            ],
            "individuals": [
                {"name": i.name, "archetype": i.archetype, "capital": i.resources.capital}
                for i in world.individuals
            ],
            "events": {
                "trades": _plain(tick.trades),
                "espionage": _plain(tick.espionage_events),
                "wmd": _plain(tick.wmd_attempts),
                "vigilante": _plain(tick.vigilante_interventions),
                "council_votes": _plain(tick.council_votes),
                "member_exits": _plain(tick.member_exits),
                "payroll": _plain(tick.payroll),
            },
        })

    def record_news(self, entries: list[str]) -> None:
        self.write("news", {"entries": entries})

    def close(self) -> None:
        for handle in self._handles.values():
            handle.close()
        self._handles.clear()


_active: RunRecorder | None = None


def active() -> RunRecorder | None:
    return _active


def start_run(label: str, meta: dict[str, Any], root: Path | None = None) -> RunRecorder:
    global _active
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    _active = RunRecorder((root or RUNS_ROOT) / f"{stamp}_{label}", meta)
    return _active


def stop_run() -> None:
    global _active
    if _active is not None:
        _active.close()
    _active = None
