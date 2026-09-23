"""causal v5 denominator meter (plan section 7) -- a read-only observer.

Designer decision K2: denominators are measured, never rounded away. After
every merge the executor hands this meter the new state and the events; the
meter records the bit lengths of numerators and denominators of time,
positions, velocities, energies and the angular-momentum residual. It
never writes back, and turning it on must not change the canonical result
(`tests/test_v5_reference.py`).

Wall-clock timing here uses floats (`time.perf_counter`) -- allowed because
it is not physics and never enters a canonical result.
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
        self.rows: list[dict[str, int]] = []
        self._started = time.perf_counter()

    def record(self, spec: WorldSpecV5, state: StateV5, events) -> None:
        values = {"time": [state.time],
                  "position": [c for e in state.elements for c in e.position],
                  "velocity": [c for s in state.structures for c in state.velocity(spec, s)],
                  "kinetic": [state.kinetic_energy(spec, s) for s in state.structures],
                  "internal": [s.internal_energy for s in state.structures],
                  "residual": [e.angular_momentum_residual for e in events]}
        row: dict[str, int] = {}
        for name, numbers in values.items():
            bits = [_bits(Fraction(n)) for n in numbers] or [(0, 0)]
            row[f"{name}_num_bits"] = max(b[0] for b in bits)
            row[f"{name}_den_bits"] = max(b[1] for b in bits)
        self.rows.append(row)

    def summary(self) -> dict[str, object]:
        out: dict[str, object] = {"events": len(self.rows),
                                  "wall_seconds": time.perf_counter() - self._started}
        if self.rows:
            for key in self.rows[0]:
                series = [r[key] for r in self.rows]
                out[key] = {"max": max(series), "median": median(series), "last": series[-1]}
        return out
