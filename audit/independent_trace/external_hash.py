"""Third opinion on the records file — computed outside Python entirely.

`verifier.py` already hashes the records file with `hashlib`. That shares an
implementation with the engine, so a bad `hashlib` (or a bad read) would agree
with itself. Shelling out to `sha256sum` costs almost nothing and removes that
last shared component for the one check that is simple enough to do this way.

This is a supplementary check. If `sha256sum` is unavailable the result says
so and reports `available=False`; it never fabricates a verdict.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExternalHashResult:
    available: bool
    digest: str | None
    tool: str | None
    detail: str

    def canonical(self) -> dict[str, object]:
        return {"available": self.available, "detail": self.detail,
                "digest": self.digest, "tool": self.tool}


def sha256_via_external_tool(path: Path) -> ExternalHashResult:
    """Hash `path` with the system `sha256sum`, if there is one."""
    path = Path(path)
    if not path.is_file():
        return ExternalHashResult(False, None, None, f"no file at {path}")
    try:
        completed = subprocess.run(
            ["sha256sum", "--binary", str(path)],
            capture_output=True, text=True, timeout=120, check=False)
    except (OSError, subprocess.SubprocessError) as error:
        return ExternalHashResult(False, None, "sha256sum", f"could not run sha256sum: {error}")
    if completed.returncode != 0:
        return ExternalHashResult(
            False, None, "sha256sum",
            f"sha256sum exited {completed.returncode}: {completed.stderr.strip()}")
    # GNU coreutils prefixes the line with a backslash when the file name it
    # echoes back contains one — which every Windows path does. The digest
    # itself is unaffected, so strip the marker rather than reject the line.
    token = completed.stdout.split(" ", 1)[0].strip().lstrip("\\")
    if len(token) != 64 or any(char not in "0123456789abcdef" for char in token):
        return ExternalHashResult(
            False, None, "sha256sum", f"unexpected sha256sum output: {completed.stdout!r}")
    return ExternalHashResult(True, token, "sha256sum", "computed by external sha256sum")
