"""Grammar v3 + probe contract, frozen before G12 (designer decision, 2026-09-24).

G12 tests B on a world it has never seen, designed by someone who does not
know the grammar. That test only means something if B's method was fixed
*before* the world existed -- otherwise the method can be quietly tuned to
the answer. So the files below are pinned by content:

  B's method      probe_grammar, probe_induction, probe_planning, probe_research
  probe contract  blind_probe (what B is told and sees), blind_probe_evaluator
                  (how the real world is translated to B's symbols),
                  probe_world (the probe's body: its five primitives)

If one of these tests fails, do NOT update the digest to make it pass.
A change to B's method or the contract is a new version (grammar v3.1 /
contract v2) in new files, decided by the designer, and G12 results are
reported against the version they ran on. See docs/current/PROBE_V3_FREEZE.md.

Line endings are normalised (CRLF -> LF) so a checkout setting cannot
break or fake the freeze.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from engine.deterministic.probe_grammar import GRAMMAR_DIGEST

PACKAGE = Path(__file__).resolve().parents[1] / "engine" / "deterministic"

FROZEN = {
    "probe_grammar": "8add42d9032e8036300508d7eda7a4b3dfcdcb73fb98f6244025ca45a61b8a3c",
    "probe_induction": "d07074853b667a5f42e3d3cf56ae59cc320bb3cd99af7ad4e87b25d4d11b8e39",
    "probe_planning": "f195442bb3d97dea72fefc6116e2d43dfc463bcac8b2456610e2d41fceddd9af",
    "probe_research": "5065871be2fb5641814d40c58aedb42afeec93cd74634898b9b6caec991b510b",
    "blind_probe": "d37332d53622dc8d2c813b9b230e0016fe62806217d9bd89184b3099e7cdc55c",
    "blind_probe_evaluator": "d27f4b97cd2aa3b4ffafd57314ab5e210fcc8a2a0b6a862aac2b7d0a7ba2e0aa",
    "probe_world": "d13699e99bab86c0209e7e85c85dbc06f32ac69de4b556de967aeaf5a5d0abe0",
}


def _digest(module: str) -> str:
    raw = (PACKAGE / f"{module}.py").read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize("module", sorted(FROZEN))
def test_frozen_file_is_unchanged(module) -> None:
    assert _digest(module) == FROZEN[module], (
        f"{module}.py is frozen for G12 -- make a new version instead of editing it "
        "(docs/current/PROBE_V3_FREEZE.md)")


def test_the_grammar_itself_is_the_v3_grammar() -> None:
    assert GRAMMAR_DIGEST == "7aff4cd75b1bf9675c818343dc507a2abfc78d888b962069cf9397c2ea48c155"


def test_line_endings_do_not_change_the_digest(tmp_path) -> None:
    text = (PACKAGE / "probe_grammar.py").read_bytes().replace(b"\r\n", b"\n")
    crlf = text.replace(b"\n", b"\r\n")
    assert hashlib.sha256(crlf.replace(b"\r\n", b"\n")).hexdigest() == FROZEN["probe_grammar"]
