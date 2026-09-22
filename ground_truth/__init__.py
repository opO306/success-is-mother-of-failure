"""Independent ground-truth answer key -- not audit tooling itself.

This package answers one question only: *for these small worlds, is the
causal structure we intend to grade B against actually true of A?* It
never asks how well B found that structure -- that comparison, if it ever
happens, is a separate tool that reads this package's sealed output files.

Four worlds, not three: GT-1 (`gt1_physical_mediator_legacy.py`) is kept as
a reference sanity check against the real A0 bond/heat physics, but is
**not** the canonical mediator benchmark -- A0 has no public control that
moves the mediator independently of the source, so GT-1's "block the
mediator" intervention has to change the whole world rather than just the
mediator. GT-M1 (`gt_m1_mediator.py`) is the canonical benchmark: a
purpose-built synthetic world where the mediator has its own public
control, so the three mediator-defining interventions can be run in the
strict, single-world sense. See both modules' docstrings.

It lives at the repo root rather than under `audit/` on purpose: `audit/`
holds *auditors* -- code that independently re-checks something the engine
already produced -- and its one hard rule is that nothing under it may
import `engine` at all (`tests/test_audit_independent_trace.py`). This
package is the opposite kind of thing: it is the answer key that an auditor
would read, and World 1 has to drive the A0 engine directly to build that
answer, so it cannot live inside `audit/` without weakening that rule for
everything else in there. `audit/` keeps its original invariant unweakened;
this package has its own, narrower one instead (see below).

Import boundary (the reason this exists as its own package rather than
reusing `engine.deterministic`'s existing test worlds):

  ALLOWED   `engine.deterministic.causal_kernel`, `causal_spec` -- the A0
            physics kernel itself and its world-spec loader. World 1 drives
            this kernel directly, tick by tick, to intervene on it.
  FORBIDDEN everything from B0.3 upward: `mechanism_candidate`,
            `causal_path_builder`, `missing_link_investigator`,
            `missing_link_hypothesis`, `causal_edge*`, `causal_timeline`,
            `trace_model`, `research_journal`, or any module that reads a
            `MechanismCandidate`/`CausalPath`/`MissingLinkHypothesis`. If a
            module here ever needs one of those, that is a sign the
            ground-truth answer is being inferred from B's own output --
            the exact circularity this package exists to prevent.

GT-2, GT-3, and GT-M1 do not touch A0's bond/heat physics at all. Reusing the
heat/bond world for "direct", "conditional", or "mediator with an
independent control" scenarios would mean editing the same engine whose
answer GT-1 is trying to establish independently -- so all three are tiny,
free-standing pure functions with no shared state with `causal_kernel`,
defined entirely in this package.

See `README.md` for the audit protocol and how to read a sealed report.
"""
from .gt1_physical_mediator_legacy import audit_world1_mediator
from .gt_m1_mediator import audit_world_m1_mediator
from .report import VERDICTS, CheckResult, GroundTruthReport
from .world2_direct import audit_world2_direct
from .world3_conditional import audit_world3_conditional

__all__ = [
    "VERDICTS",
    "CheckResult",
    "GroundTruthReport",
    "audit_world1_mediator",
    "audit_world2_direct",
    "audit_world3_conditional",
    "audit_world_m1_mediator",
]
