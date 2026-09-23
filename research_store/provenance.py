"""Where a stored record came from: code version, research semantics, run inputs.

`dirty` policy (part of the store contract, docs/current/RESEARCH_STORE_V1.md):
a record is dirty when any *tracked* file outside `.claude/` differs from
the commit. `.claude/` is excluded because it holds editor/agent tool state
(session locks, local skills), never code that produces research data; a
stale lock file committed there by accident must not mark every record
irreproducible. Untracked files are ignored (they cannot be imported by
committed code without also being committed). Nothing else is excluded.

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
BLIND_RESEARCH_SEMANTICS = "blind-research/g8/grammar-v2/observe-first/notice-delayed"
# History (older labels stay valid in stored records; never reused):
#   .../validate-full                 first 18 runs, 2026-09-23 -- journal had
#                                     no experiment_candidate_ranked entries
#   .../validate-full/selection-log   journal records phase, horizon and
#                                     expected splits for every experiment
#   .../selection-log/evidence-limits final hypotheses carry evidence links;
#                                     journal and outcome carry B's own
#                                     limitation assessment per question
#   blind-research/g8/grammar-v2/...  G8: observation-only first run sets
#                                     observed initial values; surprise ->
#                                     noticed DELAYED hypotheses (grammar v2)


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
