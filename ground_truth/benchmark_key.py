"""G7.4: the blind-research benchmark answer key -- loader and validator.

The answer key itself is the declarative files in `ground_truth/benchmark/`,
one per scenario, written by hand from the hidden rule functions
(`synthetic_kernel.RULE_S0x`) and each scenario's interface -- never from
B's code or from any B run. They are committed and sealed (see
`key_digest`) before the scorer that reads them exists, and the benchmark
script builds each scenario's real world *from* these files, so the world
B is run on and the world the key describes cannot drift apart.

Two truth layers per target, never merged into one field:

  structural_claim        what the world actually does (may be unstatable
                          by B: a hidden mediator, an out-of-vocabulary form)
  best_answer             the best any B could give with this scenario's
                          controls, observables, tick budget and vocabulary:
                          `single` (one claim), `tie` (claims no allowed
                          experiment can separate), or `unexpressible`

plus declared limits (language / observation / intervention) and the
minimum observation horizon the structural effect needs.

Imports nothing from `engine` -- same boundary as the rest of this package.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "benchmark-ground-truth-v1"
KEY_DIRECTORY = Path(__file__).resolve().parent / "benchmark"

KINDS = frozenset({"NO_EFFECT", "DIRECT", "INVERTED", "CONDITIONAL", "DISJUNCTIVE", "MEDIATED"})
ANSWER_TYPES = frozenset({"single", "tie", "unexpressible"})
LIMITS = ("language_limit", "observation_limit", "intervention_limit")


class AnswerKeyError(ValueError):
    """An answer-key file is malformed."""


def _check_claim(claim: Any, target: str, where: str) -> None:
    if not isinstance(claim, dict) or claim.get("kind") not in KINDS:
        raise AnswerKeyError(f"{where}: claim needs a known kind")
    if claim.get("target") != target:
        raise AnswerKeyError(f"{where}: claim target must be {target!r}")
    if not isinstance(claim.get("causes"), list):
        raise AnswerKeyError(f"{where}: causes must be a list")
    if (claim["kind"] == "MEDIATED") != ("mediator" in claim):
        raise AnswerKeyError(f"{where}: mediator required for MEDIATED only")


def validate_scenario(key: Mapping[str, Any]) -> None:
    sid = key.get("scenario_id")
    if key.get("format") != FORMAT or not isinstance(sid, str):
        raise AnswerKeyError(f"{sid}: wrong format or missing scenario_id")
    world = key.get("world", {})
    for field in ("world_id", "world_revision", "variables", "initial_values", "public_controls",
                  "public_observables", "ticks"):
        if field not in world:
            raise AnswerKeyError(f"{sid}: world.{field} missing")
    targets = key.get("targets", {})
    if set(targets) != set(world["public_observables"]):
        raise AnswerKeyError(f"{sid}: exactly one target entry per public observable")
    for target, entry in targets.items():
        where = f"{sid}.{target}"
        if entry.get("structural_claim") is not None:
            _check_claim(entry["structural_claim"], target, where + ".structural_claim")
        answer = entry.get("best_answer", {})
        if answer.get("type") not in ANSWER_TYPES:
            raise AnswerKeyError(f"{where}: best_answer.type must be one of {sorted(ANSWER_TYPES)}")
        claims = answer.get("claims", [])
        expected = {"single": 1, "unexpressible": 0}.get(answer["type"])
        if expected is not None and len(claims) != expected:
            raise AnswerKeyError(f"{where}: {answer['type']} answer needs {expected} claim(s)")
        if answer["type"] == "tie" and len(claims) < 2:
            raise AnswerKeyError(f"{where}: a tie needs at least two claims")
        for claim in claims:
            _check_claim(claim, target, where + ".best_answer")
        if set(entry.get("limits", {})) != set(LIMITS):
            raise AnswerKeyError(f"{where}: limits must declare exactly {LIMITS}")
        for flag in ("expressible_structurally", "expressible_observationally", "hidden_variable_present"):
            if not isinstance(entry.get(flag), bool):
                raise AnswerKeyError(f"{where}: {flag} must be true/false")
        horizon = entry.get("minimum_observation_horizon")
        if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 1:
            raise AnswerKeyError(f"{where}: minimum_observation_horizon must be a positive integer")


def load_answer_key(directory: Path = KEY_DIRECTORY) -> dict[str, dict[str, Any]]:
    """Every scenario in `directory`, validated, keyed by scenario_id."""
    key: dict[str, dict[str, Any]] = {}
    for path in sorted(Path(directory).glob("*.json")):
        scenario = json.loads(path.read_text(encoding="utf-8"))
        validate_scenario(scenario)
        if scenario["scenario_id"] != path.stem:
            raise AnswerKeyError(f"{path.name}: scenario_id must equal the file name")
        key[scenario["scenario_id"]] = scenario
    if not key:
        raise AnswerKeyError(f"no answer-key files in {directory}")
    return key


def key_digest(key: Mapping[str, Any]) -> str:
    raw = json.dumps(key, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
