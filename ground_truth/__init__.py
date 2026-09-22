"""Independent ground-truth audit: builds the answer key B is graded against.

This package answers one question only: *for these three small worlds, is
the causal structure we intend to grade B against actually true of A?* It
never asks how well B found that structure -- that comparison, if it ever
happens, is a separate tool that reads this package's sealed output files.

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

World 2 and World 3 do not touch A0's bond/heat physics at all. Reusing the
heat/bond world for "direct" and "conditional" scenarios would mean editing
the same engine whose mediator answer World 1 is trying to establish
independently -- so those two are tiny, free-standing pure functions with no
shared state with `causal_kernel`, defined entirely in this package.

See `README.md` for the audit protocol and how to read a sealed report.
"""
from .report import VERDICTS, CheckResult, GroundTruthReport
from .world1_mediator import audit_world1_mediator
from .world2_direct import audit_world2_direct
from .world3_conditional import audit_world3_conditional

__all__ = [
    "VERDICTS",
    "CheckResult",
    "GroundTruthReport",
    "audit_world1_mediator",
    "audit_world2_direct",
    "audit_world3_conditional",
]
