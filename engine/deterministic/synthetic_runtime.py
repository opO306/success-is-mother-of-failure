"""G6c-3.1: the private world_id/world_revision -> hidden rule binding.

`SyntheticWorldSpec` (B-facing) no longer names which rule governs it --
that removed the `rule_id` field a first draft carried, since a selector
string sitting in B's own research subject is exactly the kind of leak this
package's "no answer-revealing names" rule exists to prevent, even for an
anonymous-looking id like `RULE-S03`.

This module is the only place that binds a `(world_id, world_revision)`
pair to an actual rule function. `SyntheticAExecutor` is the only caller
that looks a binding up -- `SyntheticResearchAdapter` (which handles
control/observation/prediction, never execution) never imports this
module, matching `research_adapter.ResearchWorldAdapter`'s own split
between "interpret a world" and "run a world" (see `research_adapter.py`'s
module docstring).

Keying on `(world_id, world_revision)` rather than `world_id` alone is the
reproducibility guarantee: if a rule's actual behavior ever changes, its
world must get a new revision, so two runs that both claim "world_id
WORLD-S01" can never silently mean two different physical laws.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .research_world import WorldCompatibilityError
from .synthetic_kernel import RULE_S01, RULE_S02, RULE_S03, SyntheticRule


@dataclass(frozen=True)
class SyntheticWorldBinding:
    world_id: str
    world_revision: str
    rule: SyntheticRule


_BINDINGS: Mapping[tuple[str, str], SyntheticWorldBinding] = {
    ("WORLD-S01", "R-7F93C2"): SyntheticWorldBinding("WORLD-S01", "R-7F93C2", RULE_S01),
    ("WORLD-S02", "R-A18D40"): SyntheticWorldBinding("WORLD-S02", "R-A18D40", RULE_S02),
    ("WORLD-S03", "R-51E8B7"): SyntheticWorldBinding("WORLD-S03", "R-51E8B7", RULE_S03),
}


def resolve_rule(world_id: str, world_revision: str) -> SyntheticRule:
    """The only lookup surface this module exposes. Raises
    `WorldCompatibilityError` for an unbound (world_id, world_revision) pair
    -- a spec naming a world/revision nothing here recognizes is a
    configuration mistake, never something a candidate's own control values
    could cause, so this must be checked before execution begins, not
    folded into a research failure (see `causal_executor.py`'s docstring on
    the same distinction, and `synthetic_executor.py`'s use of this
    function outside its own try/except)."""
    try:
        return _BINDINGS[(world_id, world_revision)].rule
    except KeyError:
        raise WorldCompatibilityError(
            f"no synthetic world is bound to world_id={world_id!r}, world_revision={world_revision!r}") from None
