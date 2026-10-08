# ADR: ADAPTIVE_EXECUTION_REAL_LEARNING_PILOT_V0

Status: SEALED_RESEARCH_DESIGN / execution NOT_AUTHORIZED.
Date: 2026-10-08. Decider: user for paid execution and research approval.
Baseline: b2c6c0fc. Branch: codex/adaptive-execution-real-learning-pilot-v0.

## Constraints and context

V1 synthetic loop passed 77 tests, but real-session adapter is missing and the previous
guardian gave STOP_UNCONFIRMED before a separate read confirmed exited. Preserve both.
No local tests/physics, paid execution, restart/rental, push or master merge authorized.
RwForce is shared. Separate result replay is not independent force formula verification.

## Decision

Add a separate research namespace. Keep all original modules byte-identical.
The research selector consumes an approved snapshot, then maps SERIAL/W6/GPU to the
unchanged V1 fixed service. The service still owns start precision, P2, original-state
restart, fallback and GPU validation. No monkeypatch of its selector or service globals.
The initial and rollback choice uses V1 select with perf=None; historical costs are not imported.

A runs N14/T1000/p163/WALL_MIN, 5 serial and 5 W6 in alternating order. B is N12/T1000/p163/
CPU_MIN, 5 serial and 5 GPU, only if A passes and approval covers B. First serial measurement
is the pre-learning actual request and counts once. After each promotion run one new real
request using the signed profile; compare it with an independently replayed result and roll back.
Each distinct actual N/T/p requires fresh V1 checker own_pass reference, outside service timing.
If retry changes precision, preserve it, replay its actual key, and refuse this p163 cost promotion.

Session manifest contains approved Vast machine/instance, fresh session identifier, Linux boot id,
environment, complete initial-state values and code hashes. Observer records monotonic boundaries,
controller/waited-child/live-GPU CPU delta and load before/after every service. Raw service stays
intact. Completion writes a CANDIDATE automatically. Inspector rebuilds candidates from raw files
and verifies original placement/GPU eligibility/start/P2/results using unchanged independent V1
checker routines. It signs REAL_SESSION_COST_CHECKED, never a relabelled TEST_ONLY receipt.

Reuse old immutable JSON/hash-chain helpers and cryptography Ed25519. Research public roots are
provisioned before collection; inspector/manager signing identities differ. The live runner and
inspector are different modules; a separate process generates replay evidence. Research roots are
not operational keys and same UID can replace files/keys. Production activation is refused.
The witness head is a separately signed controller record, checked before every journal use;
tail truncation/fork/root tamper is detected against its provisioned head. This is functional
single-controller witness separation, not external adversarial OS isolation or remote notarization.

## Options considered

1. Loosen synthetic V1 check: small but destroys provenance; rejected.
2. Patch V1 selector/service globals: small but alters frozen behavior; rejected.
3. Separate research wrapper with unchanged executors and dedicated real verifier: selected.
   More source and replay cost, but explicit research scope, rollback and raw compatibility remain.

## Costs and bounds

Preserve 5 repeats and spread max/min<=1.25. Timing conversion is evidence accounting, not a change
to physical rounding. Compare full outer wall and OS cumulative CPU. Keep original service CPU,
sum of every attempt and preparation/worker startup separately. Clock reconciliation tolerance is
max(50ms,1 percent), sealed beforehand because live GPU OS clocks are tick-quantized.
No claim that CPU savings mean GPU energy savings. Record each overhead category, total job CPU,
actual wall, hourly rate and billing confidence. Reuse break-even is ceil(overhead/per-request saving).
One observed reuse that loses money remains COST_NOT_YET_RECOVERED. Unknown future reuse stays
UNCONFIRMED. Both speedup ratio and actual incremental saved objective are reported.

Proposed only: <=$0.25/hr, <=$0.25 total, <=60min allocation, <=54min compute, <=3min stop
confirmation, 3min startup/handoff reserve; serial campaigns, <=6 workers. Expected service-only
time from old data about18min is historical estimate, not a host guarantee. Per call480s, 2GiB.
Before each call, ensure its worst-case reservation fits remaining job budget; otherwise STOP.
No retry/reset/duration change based on observed performance. At most3 explicitly approved attempts.

## Guardian and safety

New standalone stdlib Python controller runs OUTSIDE guest, calls only exact-instance show/stop.
It rejects nonexclusive lease or price cap, observes actual stopped/exited for up to180s, retries
stop at most3. running/intended=stopped stays pending. On timeout/network/control failure, write
external warning/manual confirmation required; never success. Fake clock/CLI tests exercise the
same controller function remotely; no need for PowerShell on guest. Mock success is not live
FAILED/network/host-death validation. Required outside ARMED receipt before paid physics.

## Consequences and next gates

Source preparation and static hashes can proceed. Offline mock/fault tests need user-authorized
remote CPU resource. Seal protocol and source before execution. Report real machine/country/price/
expected time and exact approved A/B scope before paid measurement. Do not start/rent any node.
Required faults: session mix, synthetic disguise, forged promotion/approval/root, N14 GPU,
objective mix, snapshot replacement, wrong result, missing failed CPU, failed rollback,
journal tail deletion, unconfirmed stop misreported success. Preserve refusal originals.
Any integrity/correctness mismatch STOP; no automatic second-stage or rerun to hide failure.
Full initial values captured, not merely historical digest reference.

OS key separation, production activation and INDEPENDENT_FORMULA_VERIFICATION_V0 remain follow-ups.
