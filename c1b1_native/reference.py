"""The one-shot sweep (designer decision 2026-10-12) and the Python reference track that uses it (C3a, survey_only).

Sweep of a track = 2 pi turns + atan2(q) - atan2(q_start), turns = exact count of crossings of the negative x axis
(the atan2 branch cut) between consecutive substep positions. Mathematically this equals the per-substep sum of
signed angles that c1b1_method_bench.fixedpoint.FxTrack accumulates (each substep turns far less than pi); it depends
on the integer state only. The same functions serve PyOneTrack (Python arithmetic) and NativeTrack (C++ arithmetic).
"""
import mpmath as mm

from c1b1_t7.ladder import FxTrackX

SWEEP_DPS = 80


def oneshot_sweep(turns, q, q_start):
    with mm.workdps(SWEEP_DPS):
        return 2 * mm.pi * turns + mm.atan2(q[1], q[0]) - mm.atan2(q_start[1], q_start[0])


def cross_turns(x0, y0, x1, y1):
    if x0 < 0 and x1 < 0:
        if y0 >= 0 > y1:
            return 1
        if y0 < 0 <= y1:
            return -1
    return 0


class OneShotSweep:
    """Mixin: `sweep` is derived from (turns, qr, q_start); FxTrack.__init__'s assignment of 0 is accepted."""

    @property
    def sweep(self):
        return oneshot_sweep(self.turns, self.qr, self.q_start)

    @sweep.setter
    def sweep(self, value):
        if value != 0:
            raise AttributeError('the one-shot sweep is derived from the state, not stored')


class PyOneTrack(OneShotSweep, FxTrackX):
    """FxTrackX arithmetic (any force object, e.g. LangForceFX2) with the one-shot sweep."""

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.turns = 0
        self.q_start = list(self.qr)

    def advance_tick(self):
        for _ in range(self.sub):
            x0, y0 = self.qr
            self._substep()
            x1, y1 = self.qr
            self.turns += cross_turns(x0, y0, x1, y1)
        self.substeps += self.sub
        self.tick += 1
