"""G6c-3.1/G6c-3.2: the private world_id/world_revision -> hidden rule binding.

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
*intended* reproducibility guarantee, but by itself it is a promise kept by
discipline, not by anything checked: nothing stops someone from editing
`RULE_S01`'s actual behavior in `synthetic_kernel.py` without also minting
a new revision here, at which point `spec.digest` would keep claiming "same
world" over two different physical laws -- silently. `_SEALED_FINGERPRINTS`
closes that gap: each binding is sealed against a hash of its rule
function's *source code* (via `inspect.getsource`), checked once at import
time. If `RULE_S01`'s implementation changes, its fingerprint changes, this
module fails to import, and the mismatch is impossible to miss -- forcing
whoever changed the rule to consciously mint (and record here) a new
revision for it.

The fingerprint hashes source *text*, never the rule's truth table (every
input mapped to its output). Hashing the truth table would hand B something
close to an oracle: a small boolean rule's full behavior can be brute-forced
and compared against a leaked hash, which defeats blindness in a way a
source-code hash -- meaningless without the source itself, which B is never
given (see this package's threat model, `synthetic_spec.py`'s module
docstring) -- does not.
"""
from __future__ import annotations

import hashlib
import inspect
from dataclasses import dataclass
from typing import Mapping

from .research_world import WorldCompatibilityError
from .synthetic_kernel import RULE_S01, RULE_S02, RULE_S03, SyntheticRule


def _fingerprint(rule: SyntheticRule) -> str:
    return hashlib.sha256(inspect.getsource(rule).encode("utf-8")).hexdigest()


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

# Sealed once, by hand, the first time each binding was recorded above.
# Regenerate a value here ONLY as part of consciously minting a new
# world_revision for that binding -- never to make a post-hoc rule edit
# "pass" under an unchanged revision. See module docstring.
_SEALED_FINGERPRINTS: Mapping[tuple[str, str], str] = {
    ("WORLD-S01", "R-7F93C2"): "bcc4ad69ffe370cf2fc77f7ea3b27b4c70a6c015999487afa91914be8629a337",
    ("WORLD-S02", "R-A18D40"): "ee296116ad5197098a4e97645861a8de2eb2b9a1545b6ee82fe029945744b899",
    ("WORLD-S03", "R-51E8B7"): "524ae71038f5cc35d48b9360d764e4354470ef4bec3a943954c664f2841a1ae6",
}


def _verify_sealed_fingerprints() -> None:
    mismatches = [key for key, binding in _BINDINGS.items()
                 if _fingerprint(binding.rule) != _SEALED_FINGERPRINTS.get(key)]
    if mismatches:
        raise WorldCompatibilityError(
            f"rule implementation changed without minting a new world_revision for: {mismatches} -- "
            f"see synthetic_runtime.py's module docstring before regenerating a sealed fingerprint")


_verify_sealed_fingerprints()


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
