"""Replayable chance and observer-isolated append-only history.

The world never receives a recorder.  A stochastic source returns both the sampled
value and an immutable draw record; the outer runner may append that record after
the world transition.  Recording therefore cannot consume randomness or feed a
value back into the simulated world.
"""
from __future__ import annotations

import copy
import base64
import hashlib
import json
import math
import random
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping


ZERO_HASH = "0" * 64


def _json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("event data must be finite JSON data") from exc


def _finite_time(value: float) -> float:
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError("world_time must be finite and non-negative")
    return value


@dataclass(frozen=True)
class WorldEvent:
    """Immutable copy of one world-side fact offered to an outside observer."""

    world_time: float
    event_type: str
    payload_json: str
    subject_id: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "world_time", _finite_time(self.world_time))
        if not self.event_type:
            raise ValueError("event_type cannot be empty")
        if self.subject_id is not None and not isinstance(self.subject_id, int):
            raise TypeError("subject_id must be an integer or None")
        try:
            payload = json.loads(self.payload_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("payload_json must contain valid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("event payload must be a JSON object")
        object.__setattr__(self, "payload_json", _json(payload))

    @classmethod
    def create(
        cls,
        world_time: float,
        event_type: str,
        payload: Mapping[str, Any] | None = None,
        subject_id: int | None = None,
    ) -> WorldEvent:
        return cls(world_time, event_type, _json(dict(payload or {})), subject_id)

    def payload(self) -> dict[str, Any]:
        """Return a fresh copy so an observer cannot mutate the event."""
        return json.loads(self.payload_json)

    def canonical(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "payload": self.payload(),
            "subject_id": self.subject_id,
            "world_time": self.world_time,
        }


@dataclass(frozen=True)
class RecordedEvent:
    sequence: int
    previous_hash: str
    event: WorldEvent
    digest: str

    def canonical_without_digest(self) -> dict[str, Any]:
        return {
            "event": self.event.canonical(),
            "previous_hash": self.previous_hash,
            "sequence": self.sequence,
        }

    def canonical(self) -> dict[str, Any]:
        return {**self.canonical_without_digest(), "digest": self.digest}


def _digest(sequence: int, previous_hash: str, event: WorldEvent) -> str:
    payload = {"event": event.canonical(), "previous_hash": previous_hash, "sequence": sequence}
    return hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()


class HistoryLog:
    """Append-only hash chain owned by the observer, not by WorldGenesis."""

    def __init__(self) -> None:
        self._records: list[RecordedEvent] = []

    @property
    def records(self) -> tuple[RecordedEvent, ...]:
        return tuple(self._records)

    def append(self, event: WorldEvent) -> RecordedEvent:
        sequence = len(self._records)
        previous = self._records[-1].digest if self._records else ZERO_HASH
        record = RecordedEvent(sequence, previous, event, _digest(sequence, previous, event))
        self._records.append(record)
        return record

    def verify(self) -> bool:
        previous = ZERO_HASH
        for sequence, record in enumerate(self._records):
            if record.sequence != sequence or record.previous_hash != previous:
                return False
            if record.digest != _digest(sequence, previous, record.event):
                return False
            previous = record.digest
        return True

    def to_json_lines(self) -> str:
        return "\n".join(_json(record.canonical()) for record in self._records)

    @classmethod
    def from_json_lines(cls, text: str) -> HistoryLog:
        history = cls()
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                event_raw = raw["event"]
                event = WorldEvent.create(
                    event_raw["world_time"],
                    event_raw["event_type"],
                    event_raw["payload"],
                    event_raw["subject_id"],
                )
                record = history.append(event)
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError("invalid history record") from exc
            if raw.get("sequence") != record.sequence or raw.get("previous_hash") != record.previous_hash:
                raise ValueError("history sequence or hash chain is broken")
            if raw.get("digest") != record.digest:
                raise ValueError("history digest does not match its event")
        return history

    def random_draws(self) -> tuple[RandomDraw, ...]:
        draws = []
        for record in self._records:
            if record.event.event_type != "random.draw":
                continue
            payload = record.event.payload()
            draws.append(
                RandomDraw(
                    index=payload["index"],
                    operation=payload["operation"],
                    arguments=tuple(payload["arguments"]),
                    result=payload["result"],
                )
            )
        return tuple(draws)


@dataclass(frozen=True)
class RandomDraw:
    index: int
    operation: str
    arguments: tuple[Any, ...]
    result: bool | int | float

    def as_event(self, world_time: float) -> WorldEvent:
        return WorldEvent.create(
            world_time,
            "random.draw",
            {
                "arguments": list(self.arguments),
                "index": self.index,
                "operation": self.operation,
                "result": self.result,
            },
        )


@dataclass(frozen=True)
class RandomSample:
    value: bool | int | float
    draw: RandomDraw


@dataclass(frozen=True)
class RandomCheckpoint:
    draw_index: int
    state: tuple[Any, ...]

    def as_event(self, world_time: float) -> WorldEvent:
        return WorldEvent.create(
            world_time,
            "random.checkpoint",
            {"draw_index": self.draw_index, "state": self.state},
        )


def _seed_record(seed: int | float | str | bytes | bytearray) -> dict[str, Any]:
    if isinstance(seed, bool):
        return {"type": "int", "value": int(seed)}
    if isinstance(seed, int):
        return {"type": "int", "value": seed}
    if isinstance(seed, float):
        if not math.isfinite(seed):
            raise ValueError("random seed must be finite")
        return {"type": "float", "value": seed}
    if isinstance(seed, str):
        return {"type": "str", "value": seed}
    if isinstance(seed, (bytes, bytearray)):
        return {"type": "bytes", "base64": base64.b64encode(bytes(seed)).decode("ascii")}
    raise TypeError("unsupported random seed type")


class SeededEventSource:
    """Seeded chance for experiments: unpredictable to organisms, replayable outside."""

    def __init__(self, seed: int | float | str | bytes | bytearray) -> None:
        self._seed_record = _seed_record(seed)
        self._rng = random.Random(seed)
        self._index = 0

    @property
    def draw_count(self) -> int:
        return self._index

    def initialization_event(self, world_time: float = 0.0) -> WorldEvent:
        return WorldEvent.create(
            world_time,
            "random.initialized",
            {"algorithm": "python.random.MT19937", "seed": self._seed_record},
        )

    def _sample(
        self,
        operation: str,
        arguments: tuple[Any, ...],
        sampler: Callable[[], bool | int | float],
    ) -> RandomSample:
        result = sampler()
        draw = RandomDraw(self._index, operation, arguments, result)
        self._index += 1
        return RandomSample(result, draw)

    def unit(self) -> RandomSample:
        return self._sample("unit", (), self._rng.random)

    def bernoulli(self, probability: float) -> RandomSample:
        probability = float(probability)
        if not math.isfinite(probability) or not 0 <= probability <= 1:
            raise ValueError("probability must be between zero and one")
        return self._sample("bernoulli", (probability,), lambda: self._rng.random() < probability)

    def uniform(self, low: float, high: float) -> RandomSample:
        low, high = float(low), float(high)
        if not math.isfinite(low) or not math.isfinite(high) or high < low:
            raise ValueError("uniform bounds must be finite and ordered")
        return self._sample("uniform", (low, high), lambda: low + (high - low) * self._rng.random())

    def choice_index(self, count: int) -> RandomSample:
        if not isinstance(count, int) or count <= 0:
            raise ValueError("choice count must be a positive integer")
        return self._sample("choice_index", (count,), lambda: self._rng.randrange(count))

    def checkpoint(self) -> RandomCheckpoint:
        return RandomCheckpoint(self._index, copy.deepcopy(self._rng.getstate()))

    def restore(self, checkpoint: RandomCheckpoint) -> None:
        self._index = checkpoint.draw_index
        self._rng.setstate(copy.deepcopy(checkpoint.state))


class ReplayEventSource:
    """Return recorded draws and reject any divergence in operation or arguments."""

    def __init__(self, draws: Iterable[RandomDraw]) -> None:
        self._draws = tuple(draws)
        self._position = 0

    @classmethod
    def from_history(cls, history: HistoryLog) -> ReplayEventSource:
        return cls(history.random_draws())

    @property
    def draw_count(self) -> int:
        return self._position

    def _take(self, operation: str, arguments: tuple[Any, ...]) -> RandomSample:
        if self._position >= len(self._draws):
            raise ValueError("replay requested more random draws than were recorded")
        draw = self._draws[self._position]
        if draw.index != self._position or draw.operation != operation or draw.arguments != arguments:
            raise ValueError("replay diverged from the recorded random event")
        self._position += 1
        return RandomSample(draw.result, draw)

    def unit(self) -> RandomSample:
        return self._take("unit", ())

    def bernoulli(self, probability: float) -> RandomSample:
        return self._take("bernoulli", (float(probability),))

    def uniform(self, low: float, high: float) -> RandomSample:
        return self._take("uniform", (float(low), float(high)))

    def choice_index(self, count: int) -> RandomSample:
        return self._take("choice_index", (count,))

    def exhausted(self) -> bool:
        return self._position == len(self._draws)
