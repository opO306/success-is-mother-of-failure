"""causal v5 denominator meter (plan section 7) -- a read-only observer.

Designer decision K2: denominators are measured, never rounded away. After
every causal round (one instant, one round -- possibly several independent
merges) the executor hands this meter the new state and that round's merge
events. The meter records the bit lengths of numerators and denominators of
time, positions, velocities, energies and the angular-momentum residual. It
never writes back; turning it on must not change the canonical result.

Counts are kept apart (review, 2026-09-24): `causal_rounds` is how many
times the executor merged something at one instant; `merge_events` is how
many merges happened (two independent merges at one instant = 1 round, 2
events).

Timing: `round_seconds` is the wall time from the previous round to this
one (event search + judging + merging). The plan's "arithmetic time / total
time" cannot be separated from inside without instrumenting the executor
(which must stay plain); it is measured from outside by profiling the run
and summing time spent in `fractions` -- see the measurement script's
`arithmetic_share`. Wall clock here uses floats (`perf_counter`), allowed
because it is not physics and never enters a canonical result.
"""
from __future__ import annotations

import time
from fractions import Fraction
from statistics import median

from .v5_spec import WorldSpecV5
from .v5_state import StateV5


def _bits(value: Fraction) -> tuple[int, int]:
    return abs(value.numerator).bit_length(), value.denominator.bit_length()


class DenominatorMeter:
    def __init__(self) -> None:
        self.rows: list[dict[str, object]] = []
        self._started = time.perf_counter()
        self._last = self._started

    def record(self, spec: WorldSpecV5, state: StateV5, round_events) -> None:
        now = time.perf_counter()
        values = {"time": [state.time],
                  "position": [c for e in state.elements for c in e.position],
                  "velocity": [c for s in state.structures for c in state.velocity(spec, s)],
                  "kinetic": [state.kinetic_energy(spec, s) for s in state.structures],
                  "internal": [s.internal_energy for s in state.structures],
                  "residual": [e.angular_momentum_residual for e in round_events]}
        row: dict[str, object] = {"merge_events": len(round_events), "round_seconds": now - self._last}
        for name, numbers in values.items():
            bits = [_bits(Fraction(n)) for n in numbers] or [(0, 0)]
            row[f"{name}_num_bits"] = max(b[0] for b in bits)
            row[f"{name}_den_bits"] = max(b[1] for b in bits)
        self.rows.append(row)
        self._last = now

    def summary(self) -> dict[str, object]:
        out: dict[str, object] = {"causal_rounds": len(self.rows),
                                  "merge_events": sum(int(r["merge_events"]) for r in self.rows),
                                  "wall_seconds": time.perf_counter() - self._started}
        if self.rows:
            for key in self.rows[0]:
                if key == "merge_events":
                    continue
                series = [r[key] for r in self.rows]
                out[key] = {"max": max(series), "median": median(series), "last": series[-1]}
        return out
