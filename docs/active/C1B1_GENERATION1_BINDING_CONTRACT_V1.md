# C1-B1 Generation 1 prepared binding contract

Status: `VERIFIED FAST-PATH GENERATION / NOT FORMALLY CERTIFIED`. Generation 1 FROZEN; production default `fast_pilot3` on the integration branch. Final scope, completed gates, measured cost and unresolved obligations are recorded in the [Generation 1 closure report](C1B1_OPTIMIZATION_GENERATION1_FREEZE_V1.md).

## Scope and trust boundary

This contract changes preparation ownership and stale refusal, not exact numerical formulas. The slow reference, Candidate B primitives, physical constants, rounding source and proof/checker remain preserved. It applies to canonical FixedPoint v2 prepared production execution. Custom profiles, Binary64 and retired v1 use their prior explicit fallback. Kernel helpers used by experiments/audits retain their frozen-source preconditions; they are not standalone mutable-model executors.

Python/standard-library/builtins and the guard implementation are trusted. This is not isolation against arbitrary hostile Python code that disables a guard or edits its private internals. Ordinary supported Run metadata changes, world-parameter changes and tested replacements of the actual numerical pipeline functions are detected. Concurrent modification of a model or Run during a step is unsupported; the measured production executor is single-threaded.

## WORLD

WorldKey contains the C1-A parameter fingerprint, C1-A/C1-B1 contract versions, FX nearest-ties-even rounding contract and retardation setting. WorldBinding owns read-only parameter structure views, independently copied and typed Fraction values, typed mapping keys/scalars, original integer-pair prepared-array identities, typed LN2 upper-bound snapshot, actual pipeline/FX function and code identities. It also seals the original Candidate B coefficient-cache values using the unchanged uncached constructor at its eight declared M tiers. Equal numeric values with different types are not interchangeable: integer exponent key 3 and float key 3.0 compare equal in Python but change the frozen fingerprint and the reference calculation contract.

Preparation calculates the full parameter fingerprint once. Hot checks compare values and identities, without hashes, Fraction normalization or new algebra. Mutable Candidate B cache contents are checked only in modes that use that cache; Pilot 3 ABCD consumes immutable integer-pair world grids. A frozen-world change refuses execution; it is not accepted through silent rebuilding or a changed fingerprint assertion.

## RUN

RunKey owns immutable integer numerator/denominator pairs for dt and each mass, ordered species, position/momentum (width, frac bits), drift rule, integer precision policy and mode/variant. Separate handles capture the exact Run and profile identities. The dt view returns a new Fraction, so mutating that returned view cannot change the key. Numerator/denominator private slots must also remain integers; an equal-valued float is refused. Production Run dt is a Fraction as created by the original new_run; replacing it with an int would turn original `dt / 2` into a float and is refused before numerical entry.

Before every step the bound executor checks Run identity, mode/variant, dt type/value, species/mass values, canonical profile fields, drift, precision policy and world conditions. Unsupported changes raise ContractViolation before calling the preserved step code. Correctly bound steps use the original step code object.

## STEP and COMPONENT

Relative coordinates, R²/radius, impulse enclosure, raw drift ratios, rounded displacement and component endpoints are derived from the current step/call. They are not reused across unrelated steps or Runs. Exact drift endpoints still feed the original segment guard; stored displacement is rounded at the same original point. The impulse's per-call M cache expires with that call. Global M-grid caching stores only world constants, not trajectory results.

The original step's J_cache is retained. After a successful prepared step, execution metadata records its exact world/Run input conditions, stored relative-position inputs and raw J. A changed dt, profiles, species, mass, coordinates or J invalidates that provenance. Rebinding refuses until the caller explicitly clears J_cache; the existing old executor also refuses. This clearing is a caller action, never an automatic state repair or retry.

A supplied cache in an initial t_steps=0 state is an original REF input, including boundary fault fixtures. The executor captures that initial declaration, and then tracks subsequent caches. An untagged mature Run's cache has unknown origin: clear it explicitly before binding. Initial cache acceptance does not certify its physical provenance.

## Verification

Fault tests exercise dt/species/mass/position-F/momentum-F/other-Run changes, fingerprint/version/rounding changes, nested coefficient replacement and private-slot source-Fraction mutation, primitive constant/function/code changes, drift function/rounder and segment function changes, stale J reuse and mutable Candidate B coefficient-cache poisoning. They assert no numerical entry and unchanged Run on refusal. Rebinding after explicit cache clearing is compared to REF.

The closing campaign separately records world preparation, Run binding, hot-check costs, same-source four-mode actual production differential, directly compared CPU trajectories and full repository regression including existing CUDA/GPU tests. Endpoint arithmetic evidence and integration trajectories are distinct obligations. Neither this contract nor a finite campaign closes A-EV, native J, infinite-domain completeness or independent replay approval.
