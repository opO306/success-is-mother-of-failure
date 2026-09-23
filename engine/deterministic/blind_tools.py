"""G9: B composes its own experiment tools from primitive presses.

B's planned experiments hold every control steady for the whole run. When
those run out before a question is settled -- a noticed idea left untested,
or a tie no planned experiment breaks -- B looks for a *new kind* of
experiment: press or release one control at chosen ticks. It is given only
the primitive ("hold this control at 1 or 0 at tick t") -- never a named
procedure such as "pulse" -- and searches, by simulating its own hypotheses,
for a press pattern that is:

  * new: not a steady hold (the plan already covers those); and
  * informative: it splits a pair of B's live hypotheses, or it is a *risky*
    test of an untested idea -- the idea predicts something other than "the
    target just keeps its starting value", so the experiment could refute it.

Among informative patterns B prefers the most *severe* test of an untested
idea: one its closest rivals would fail. The rivals are the claims B already
refuted for that question, ranked by how often they agreed with the idea on
the experiments already planned -- the nearer a rival came to fitting the
data, the more a test that separates it from the idea is worth. (Holding x1
on through tick 1 cannot tell "x1 reaches x3 after 2 ticks" from its close
rival "after 1 tick"; pressing x1 only at tick 0 can.) Counting every
refuted claim equally does not do this -- measured: a far rival (the
inverted claim) then cancels a near one out and the weaker test wins the tie.

A pattern that helped is kept as a `Tool`: the press sequence, stated
relative to "the control being pressed" so it can be reused on another
variable or in another world. Before searching, B tries the tools it already
has; only if none is informative here does it compose a new one. A search
that finds nothing is recorded too (`tool_search_failed`) -- the attempt is
data, the same as a refuted hypothesis.

What this does not do, stated plainly: B searches single-control press
patterns up to the world's tick limit, a space a person chose. It invents
*which* pattern and *when* to use it; the primitive itself was given.

B-facing: imports only B-side modules (checked transitively by tests).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from itertools import product
from typing import Mapping, Sequence

from .blind_execution import BlindCandidateSpec
from .blind_hypothesis import BlindCausalClaim, predict_target
from .blind_session import BlindControlDescriptor, BlindWorldDescriptor

FORMAT = "blind-tool-v1"
DEFAULT_MAX_TOOL_EXPERIMENTS = 3


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Tool:
    """A press pattern for one control: its value at ticks 0..len-1, observed
    at tick `horizon`. Stated without naming any variable, so it can be
    applied to whichever control a later question needs pressed."""
    pattern: tuple[int, ...]
    horizon: int
    format: str = FORMAT

    def __post_init__(self) -> None:
        if not self.pattern or any(v not in (0, 1) or isinstance(v, bool) for v in self.pattern):
            raise ValueError("a tool pattern is a non-empty sequence of 0/1")
        if len(set(self.pattern)) < 2:
            raise ValueError("a steady hold is not a tool; the plan already covers it")
        if isinstance(self.horizon, bool) or not isinstance(self.horizon, int) or self.horizon < len(self.pattern) - 1:
            raise ValueError("horizon must cover the whole pattern")

    @property
    def tool_id(self) -> str:
        return f"BTOOLDEF-{_digest(self.canonical())[:16]}"

    def canonical(self) -> dict[str, object]:
        return {"format": self.format, "horizon": self.horizon, "pattern": list(self.pattern)}

    @classmethod
    def from_canonical(cls, raw: Mapping[str, object]) -> "Tool":
        return cls(tuple(raw["pattern"]), raw["horizon"])


@dataclass(frozen=True)
class ToolExperiment:
    arm_id: str
    tool: Tool
    reused: bool
    control_id: str
    question_index: int
    spec: BlindCandidateSpec
    schedule: Mapping[int, Mapping[str, bool]]
    expected_split_pairs: int
    risky_for_proposals: int
    severity_against_refuted: int
    severity_vector: tuple[int, ...] = ()


def _schedule(tool: Tool, variable: str) -> dict[int, dict[str, bool]]:
    return {tick: {variable: bool(value)} for tick, value in enumerate(tool.pattern)}


def _score(tool: Tool, variable: str, alive: Sequence[str], proposals: Sequence[str],
           claims: Mapping[str, BlindCausalClaim], target_variable: str,
           initial: Mapping[str, bool] | None, baseline: bool,
           rivals: Mapping[str, Sequence[str]] | None = None) -> tuple[int, int, tuple[int, ...]]:
    """(live pairs split, untested ideas put at risk, severity) -- compared
    as a tuple. Severity is one flag per (idea, rival), rivals closest first:
    1 when the rival predicts differently from the idea here."""
    schedule = _schedule(tool, variable)
    refuted = sorted(set(claims) - set(alive) - set(proposals))
    rivals = rivals or {hid: refuted for hid in proposals}
    predicted = {hid: predict_target(claims[hid], {}, tool.horizon, baseline, initial, schedule)
                 for hid in list(alive) + list(proposals) + refuted}
    live_ids = sorted(set(alive) | set(proposals))
    splits = sum(1 for i, a in enumerate(live_ids) for b in live_ids[i + 1:] if predicted[a] != predicted[b])
    start = (initial or {}).get(target_variable, baseline)
    risky = sum(1 for hid in proposals if predicted[hid] != start)
    severity = tuple(int(predicted[other] != predicted[hid]) for hid in sorted(proposals)
                     for other in rivals.get(hid, refuted))
    return splits, risky, severity


def _candidates(world: BlindWorldDescriptor) -> list[Tool]:
    tools = []
    for horizon in range(1, world.ticks + 1):
        for pattern in product((1, 0), repeat=horizon + 1):
            if len(set(pattern)) > 1:
                tools.append(Tool(tuple(pattern), horizon))
    return sorted(tools, key=lambda t: (t.horizon, sum(1 for a, b in zip(t.pattern, t.pattern[1:]) if a != b),
                                        tuple(-v for v in t.pattern)))


def design_tool_experiment(
    question_index: int, target_variable: str, alive: Sequence[str], proposals: Sequence[str],
    claims: Mapping[str, BlindCausalClaim], world: BlindWorldDescriptor,
    controls: tuple[BlindControlDescriptor, ...], initial: Mapping[str, bool] | None, baseline: bool,
    toolbox: Sequence[Tool], already_run: frozenset[tuple[str, str]],
    rivals: Mapping[str, Sequence[str]] | None = None,
) -> ToolExperiment | None:
    """The most informative new press experiment for one question, or None.

    Known tools first (in toolbox order), then every single-control press
    pattern in order of horizon, then fewest switches. `rivals` maps each
    untested idea to the refuted claims of its question, closest first (the
    loop ranks them by agreement on planned experiments). `already_run` holds
    (tool_id, control_id) pairs executed earlier in this run -- repeating
    one would only return data B already has.
    """
    control_of = {c.alias_variable_id: c.alias_control_id for c in controls}
    variables = sorted(v for v in control_of if v != target_variable)

    def best(pool: Sequence[Tool], reused: bool) -> ToolExperiment | None:
        chosen = None
        for tool in pool:
            if tool.horizon > world.ticks:
                continue
            for variable in variables:
                if (tool.tool_id, control_of[variable]) in already_run:
                    continue
                splits, risky, severity = _score(tool, variable, alive, proposals, claims, target_variable,
                                                 initial, baseline, rivals)
                if (splits, risky) == (0, 0):
                    continue
                if chosen is None or (splits, risky, severity) > (
                        chosen.expected_split_pairs, chosen.risky_for_proposals, chosen.severity_vector):
                    control = control_of[variable]
                    arm_id = "BTOOL-" + _digest({"control": control, "tool": tool.canonical(),
                                                 "world": world.alias_world_id})[:16]
                    schedule = tuple((tick, control, value) for tick, value in enumerate(tool.pattern))
                    chosen = ToolExperiment(arm_id, tool, reused, control, question_index,
                                            BlindCandidateSpec(world.alias_world_id, arm_id, (), tool.horizon,
                                                               schedule=schedule),
                                            _schedule(tool, variable), splits, risky, sum(severity), severity)
        return chosen

    return best(list(toolbox), True) or best(_candidates(world), False)
