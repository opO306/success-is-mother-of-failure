"""G7.3a: the evaluator-only executor that runs a real `SyntheticWorldSpec`
on B's behalf and hands back only a blind-safe `ExecutionResult`.

This is the only module that knows all three of: a `BlindTranslationManifest`
(`blind_evaluator.py`), a real `SyntheticWorldSpec`
(`synthetic_spec.py`/`synthetic_adapter.py`), and `SyntheticAExecutor`
(`synthetic_executor.py`, which itself is the only caller allowed to touch
`synthetic_runtime.resolve_rule` -- see that module's own docstring). B-facing
code never imports this module; it only ever holds a reference typed
`AExecutor` (`causal_executor.py`'s Protocol), and an external harness is
what actually constructs a `SyntheticBlindAExecutor` and hands it to
whatever B-facing entrypoint takes an executor -- see this module's own
`SyntheticBlindAExecutor` docstring for why B-facing code never constructs
one itself.

Translation direction, strictly one way per call:

    BlindCandidateSpec (B-facing, alias-only)
        -> real SyntheticWorldSpec (apply real controls, from the manifest)
        -> SyntheticAExecutor.execute (real kernel run)
        -> real ExecutionResult (real digests, real SyntheticRun)
        -> sanitize: replace every real digest/name with its alias
        -> blind-safe ExecutionResult (BlindRun, BlindCandidateSpec.digest)

The real `ExecutionResult` never escapes `SyntheticBlindAExecutor.execute` --
only the sanitized one does. `executed_spec_digest` on the returned result
is always `BlindCandidateSpec.digest` (recomputed from the alias-only spec
that was actually asked for), never `real_spec.digest`; `run` is always a
`BlindRun` built by translating each real checkpoint's observable names
through the manifest, never the real `SyntheticRun` itself. On a failed
execution, `error_message` is replaced with a fixed blind-safe string
rather than passed through -- a real exception's message or traceback could
otherwise mention a real variable/world identifier with no sanitization
step to catch it, the same class of leak `tests/test_deterministic_blind_execution.py`'s
serialization-leakage tests exist to catch on the success path.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from .blind_evaluator import BlindTranslationManifest
from .blind_execution import BlindCandidateSpec, BlindCheckpoint, BlindRun
from .causal_executor import AExecutor, ExecutionResult
from .research_world import ResearchWorldSpec, WorldCompatibilityError
from .synthetic_adapter import SyntheticControlDefinition
from .synthetic_executor import SyntheticAExecutor
from .synthetic_spec import SyntheticClamp, SyntheticWorldSpec

_BLIND_EXECUTION_FAILURE_MESSAGE = "execution failed (details withheld -- blind boundary)"

_CONTROL_MODE_FOR_VALUE = {1: "ON", 0: "OFF", None: "FREE"}


def _resolve_real_spec(real_spec: SyntheticWorldSpec, manifest: BlindTranslationManifest,
                       candidate: BlindCandidateSpec) -> SyntheticWorldSpec:
    """Apply `candidate`'s alias-only control values onto `real_spec` by
    translating each alias control id back to its real variable through
    `manifest`, producing the real spec `SyntheticAExecutor` actually runs."""
    clamps = list(real_spec.clamps)
    for alias_control_id, value in candidate.control_values:
        try:
            real_variable = manifest.real_control[alias_control_id]
        except KeyError:
            raise WorldCompatibilityError(
                f"candidate names alias control {alias_control_id!r}, which this manifest does not bind") from None
        if isinstance(value, bool) or value not in _CONTROL_MODE_FOR_VALUE:
            raise WorldCompatibilityError(f"control {alias_control_id!r} only accepts 0/1/None, got {value!r}")
        mode = _CONTROL_MODE_FOR_VALUE[value]
        clamps = [c for c in clamps if c.variable_id != real_variable]
        if mode != "FREE":
            clamps.append(SyntheticClamp(real_variable, mode))
    # G7.3b-4: `candidate.ticks` is the experiment's observation horizon.
    # Before this, it was accepted and then ignored -- every candidate ran
    # `real_spec.ticks` -- so "observe after 1 tick" and "after 2 ticks"
    # silently executed the same run. `real_spec.ticks` is now the longest
    # run the harness allows, not the length every run is forced to have.
    if candidate.ticks > real_spec.ticks:
        raise WorldCompatibilityError(
            f"candidate asks for {candidate.ticks} ticks, over this world's limit of {real_spec.ticks}")
    return replace(real_spec, clamps=tuple(sorted(clamps)), ticks=candidate.ticks)


def _blind_run_from_real(real_result: ExecutionResult, manifest: BlindTranslationManifest,
                         alias_world_id: str) -> BlindRun:
    """Translate a real `SyntheticRun`'s checkpoints into alias-only
    `BlindCheckpoint`s. Requires `real_result.run` to be a `SyntheticRun` --
    callers only reach here after confirming `real_result.status == "success"`."""
    checkpoints = []
    for real_checkpoint in real_result.run.checkpoints:
        alias_values = tuple(sorted(
            (manifest.observable_alias[name], value) for name, value in real_checkpoint.values
            if name in manifest.observable_alias
        ))
        checkpoints.append(BlindCheckpoint(real_checkpoint.tick, alias_values))
    return BlindRun(alias_world_id, tuple(checkpoints))


@dataclass(frozen=True)
class SyntheticBlindAExecutor:
    """The `AExecutor` a blind B-facing entrypoint is handed -- an external
    harness constructs this (with a real spec and its manifest) and passes
    it in as `executor: AExecutor`; B-facing code never imports this class
    or `synthetic_executor`/`synthetic_runtime`/`blind_evaluator` itself.
    This is the dependency inversion this Gate exists to set up: B knows
    the `AExecutor` Protocol's shape, never this implementation.
    """
    real_spec: SyntheticWorldSpec
    manifest: BlindTranslationManifest

    def execute(self, spec: ResearchWorldSpec) -> ExecutionResult:
        if not isinstance(spec, BlindCandidateSpec):
            raise WorldCompatibilityError(
                f"SyntheticBlindAExecutor requires a BlindCandidateSpec, got {type(spec).__name__}")
        if spec.world_id != self.manifest.alias_world_id:
            raise WorldCompatibilityError(
                f"candidate names world {spec.world_id!r}, which does not match this executor's "
                f"bound alias world {self.manifest.alias_world_id!r}")

        resolved_real_spec = _resolve_real_spec(self.real_spec, self.manifest, spec)
        real_result = SyntheticAExecutor().execute(resolved_real_spec)

        if real_result.status == "failed":
            return ExecutionResult("failed", spec.digest, None, real_result.error_kind,
                                   _BLIND_EXECUTION_FAILURE_MESSAGE)

        blind_run = _blind_run_from_real(real_result, self.manifest, spec.world_id)
        return ExecutionResult("success", spec.digest, blind_run)
