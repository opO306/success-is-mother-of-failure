"""Where a stored record came from: code version, research semantics, run inputs.

`semantics` names the *meaning* the data was produced under (which Gate's
rules, which hypothesis vocabulary and time rule), separately from the git
commit: two commits can share semantics (a refactor), and one semantics
label must change whenever results stop being comparable. Readers must
choose a semantics explicitly (`b_visible.BVisibleReader.records`), so
results from incompatible rules are never mixed by accident.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

# Bump whenever blind-research results stop being comparable with earlier
# ones (vocabulary, time rule, baseline prior, plan shape, loop verdicts).
BLIND_RESEARCH_SEMANTICS = "blind-research/g7.3c/vocab6/tick1/baseline-false/validate-full"


def git_state(repo_root: Path) -> tuple[str, bool]:
    """(commit, dirty). Unknown outside a git checkout -- recorded, not hidden."""
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root, capture_output=True,
                                text=True, check=True).stdout.strip()
        # `.claude/` is editor/agent tool state, not code that produces
        # research data -- a stale lock file there must not mark every
        # record as irreproducible.
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--untracked-files=no", "--", ".",
                                     ":!.claude"], cwd=repo_root,
                                    capture_output=True, text=True, check=True).stdout.strip())
        return commit, dirty
    except (OSError, subprocess.CalledProcessError):
        return "unknown", True


def provenance(repo_root: Path, semantics: str, producer: str) -> dict[str, object]:
    """A dirty working tree is allowed but recorded: such a record cannot be
    reproduced from its commit alone, and readers can filter on it."""
    commit, dirty = git_state(repo_root)
    return {"commit": commit, "dirty": dirty, "producer": producer, "semantics": semantics}
