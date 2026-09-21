"""BrainAdapter boundary and the first exact-oracle adapter.

The exact adapter is a regression oracle, not a mandated reasoning method.
Future adapters may use unrelated internal representations and emit different
claim kinds as long as their external claims carry testable evidence bridges.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from .b_language import (
    BoundaryEvaluation,
    CapabilityManifest,
    Claim,
    ClaimSet,
    EvidenceBridge,
    ObservationContract,
)
from .causal_kernel import CausalRun, initial_causal_state
from .causal_spec import CausalWorldSpec
from .environment_kernel import EnvironmentRun, initial_environment_state
from .environment_spec import EnvironmentWorldSpec
from .environment_world_model import forecast_environment_world
from .world_model import forecast_world


@runtime_checkable
class BrainAdapter(Protocol):
    @property
    def manifest(self) -> CapabilityManifest: ...

    def respond(self, challenge: ObservationContract,
                spec: CausalWorldSpec | EnvironmentWorldSpec) -> ClaimSet: ...


def make_prediction_challenge(
    spec: CausalWorldSpec | EnvironmentWorldSpec, ticks: int | None = None,
) -> ObservationContract:
    if isinstance(spec, EnvironmentWorldSpec):
        horizon = min(spec.causal_world.ticks, 10) if ticks is None else ticks
        world_id = spec.causal_world.world_id
        initial_digest = initial_environment_state(spec).digest
        cells = spec.causal_world.kernel.width * spec.causal_world.kernel.height
    elif isinstance(spec, CausalWorldSpec):
        horizon = min(spec.ticks, 10) if ticks is None else ticks
        world_id = spec.world_id
        initial_digest = initial_causal_state(spec).digest
        cells = spec.kernel.width * spec.kernel.height
    else:
        raise TypeError("unsupported world specification")
    if isinstance(horizon, bool) or not isinstance(horizon, int) or not 0 <= horizon <= 10:
        raise ValueError("prediction challenge horizon must be from zero through 10")
    return ObservationContract(
        f"{world_id}:state-prediction:{horizon}", "predict_state_digest",
        (("spec", spec.digest), ("initial_state", initial_digest)),
        ("sealed_spec", "initial_state"), ("actual_future_checkpoints",), horizon,
        cells * max(1, horizon), cells * 8 * 16,
        ("submitted state digests match held-out A checkpoints",),
    )


class ExactOracleAdapter:
    """Expose existing exact forecasts through the model-neutral boundary."""

    def __init__(self) -> None:
        self._manifest = CapabilityManifest(
            "exact-a-oracle", "deterministic-transition-oracle", "1",
            ("predict_state_digest", "explain_local_transition"),
            ("sealed_spec", "initial_state"), "private sealed A-transition clone", True,
        )

    @property
    def manifest(self) -> CapabilityManifest: return self._manifest

    def respond(self, challenge: ObservationContract,
                spec: CausalWorldSpec | EnvironmentWorldSpec) -> ClaimSet:
        if challenge.task_kind != "predict_state_digest":
            raise ValueError("exact oracle does not support this task kind")
        if challenge.visible_digest("spec") != spec.digest:
            raise ValueError("challenge spec digest does not match supplied specification")
        if isinstance(spec, EnvironmentWorldSpec):
            expected_initial = initial_environment_state(spec).digest
            forecast = forecast_environment_world(spec, challenge.max_ticks)
        elif isinstance(spec, CausalWorldSpec):
            expected_initial = initial_causal_state(spec).digest
            forecast = forecast_world(spec, challenge.max_ticks)
        else:
            raise TypeError("unsupported world specification")
        if challenge.visible_digest("initial_state") != expected_initial:
            raise ValueError("challenge initial-state digest does not match supplied specification")
        claims = []
        bridges = []
        for step in forecast.steps:
            claim_id = f"tick-{step.tick}-state"
            payload = {"predicted_events": list(step.predicted_events),
                       "state_digest": step.after_digest, "tick": step.tick,
                       "total_energy": step.total_energy}
            claims.append(Claim(claim_id, "state_digest_prediction", "exact", spec.digest, payload))
            bridges.append(EvidenceBridge(
                claim_id, "compare_held_out_a_checkpoint", (spec.digest, expected_initial),
                {"state_digest": step.after_digest, "tick": step.tick},
                ("actual checkpoint is absent", "actual state digest differs"),
            ))
        return ClaimSet(challenge.digest, self.manifest.digest, tuple(claims), tuple(bridges))


def evaluate_state_digest_claims(
    challenge: ObservationContract, claim_set: ClaimSet,
    run: CausalRun | EnvironmentRun,
) -> BoundaryEvaluation:
    if claim_set.challenge_digest != challenge.digest:
        raise ValueError("claim set belongs to another challenge")
    expected_spec = challenge.visible_digest("spec")
    if expected_spec != run.spec_digest:
        raise ValueError("run specification does not match challenge")
    actual = {item.tick: item.state_digest for item in run.checkpoints}
    verified = []
    falsified = []
    untested = []
    findings = []
    for claim in claim_set.claims:
        if claim.claim_kind != "state_digest_prediction":
            untested.append(claim.claim_id)
            findings.append({"claim_id": claim.claim_id, "reason": "no evaluator for claim kind"})
            continue
        tick = claim.payload.get("tick")
        predicted = claim.payload.get("state_digest")
        observed = actual.get(tick)
        if observed is None:
            untested.append(claim.claim_id)
            findings.append({"claim_id": claim.claim_id, "reason": "actual checkpoint is absent", "tick": tick})
        elif predicted == observed:
            verified.append(claim.claim_id)
        else:
            falsified.append(claim.claim_id)
            findings.append({"actual": observed, "claim_id": claim.claim_id,
                             "predicted": predicted, "reason": "state digest differs", "tick": tick})
    return BoundaryEvaluation(challenge.digest, claim_set.digest, run.digest,
                              tuple(verified), tuple(falsified), tuple(untested), tuple(findings))
