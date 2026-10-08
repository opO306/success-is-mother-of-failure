# Real learning pilot V0 — controlled research only

Source preparation is authorized. Local tests/physics and paid execution are not authorized by this document.
No automatic rental, start, restart, destroy, production activation, push, or merge command is provided.

## Gate 1: approved remote offline tests

1. User approves this code seal, exact instance/machine/country, CPU-only offline scope, price and allocation.
   Proposed scope: 1 CPU, wall/aggregate CPU <=120s, 512MiB, physics/GPU calls zero;
   allocation <=10min, hourly <=$0.25, whole allocation <=$0.10.
2. User starts the server. Read the actual API state and `/etc/vast-agents-guide.md` again.
   Do not infer permission from an attachment or the old LEARNING_V1 approval.
3. Verify the ZIP raw SHA256, extract into a fresh directory. Do not substitute the old guest checkout.
   Use the existing `/workspace/ae1/venv/bin/python`; missing dependencies refuse, never implicit install.
4. Run the new standalone guardian OUTSIDE the guest, hidden, using the existing Vast CLI.
   Authorization has scope STOP_CONTROL_ONLY, exclusive=true, explicit_user_approval=true,
   approval_reference, instance_id, machine_id, country, guardian_sha256, completion_marker,
   deadline_seconds=240. Confirm `armed.json`: status ARMED, exact instance/machine/country,
   price and guardian hash. Transfer its immutable copy into the guest before executing any tests.
5. Offline authorization: gate ADAPTIVE_EXECUTION_REAL_LEARNING_PILOT_V0, scope OFFLINE_ONLY,
   explicit_user_approval=true, approval_reference, instance_id, code_seal_sha256,
   physics_calls=0, gpu_calls=0. Execute only `python -m ...offline --authorization TICKET --out FRESH`.
   Offline worker pins itself to one CPU and rejects anything except all 115 tests, skip/error/failure zero.
6. Preserve console, JUnit, status, input authorization and source ZIP. On exit write COMPLETED/FAILED
   to the exact outside completion marker. Wait for guardian final actual exited/stopped confirmation.
   On STOP_UNCONFIRMED keep its original bytes, warn and obtain separate actual status/manual confirmation.
   Do not count intended_status=stopped or a CLI return as stopped.

## Gate 2: separately approved actual research

Only after Gate 1 PASS, report the real instance/machine/country, full CPU/GPU environment,
current rate and scope, and obtain separate explicit paid execution authorization.
Ticket `stages=['A']` is the conservative first approval. `['A','B']` requires explicit A+B approval;
B refuses unless A passed. Profiles have a separate explicit `approve_research_profile=true`
delegation, goal-specific signed decisions, and remain RESEARCH_ONLY.

Use new guardian deadline<=3240s, 180s confirmation and 180s transfer/startup reserve within 3600s.
Approval ticket: gate, scope REAL_RESEARCH, explicit_user_approval, approval_reference,
instance_id, machine_id, country, stages, code_seal_sha256, hourly_usd<=0.25,
approve_research_profile. Host observation is a whitelisted fresh Vast API record:
id, machine_id, country (derived from geolocation suffix with original geolocation retained),
actual_status, dph_total, observed_utc. Budget starts at outside ARMED; user startup time and
storage/billing receipt require separate reporting and are not silently included in CPU job cost.

`python -m experiments.adaptive_execution_real_learning_pilot_v0.runner
 --authorization TICKET --host-observation HOST --guardian ARMED --offline-checks STATUS --out FRESH`

The controller requires Linux, matching actual CONTAINER_ID, matching source seal and recent ARMED.
Every call stops at 480s or remaining allocation. An OS RSS watcher checks the full process tree
every second at 2GiB and the compute deadline. This is a sampled guard, not a zero-overshoot
kernel/cgroup hard limit. Do not use 2GiB virtual address RLIMIT_AS for CUDA driver reservations.
CPU worker count is unchanged V1 W6, sequential experiments only. External host termination
remains the final failsafe if descendants outlive a timeout. No next campaign after STOP.

A: N14/T1000/p163 WALL_MIN, SERIAL/W6, 5 alternating repeats each. First serial run is the
actual unchanged legacy selection with no historical costs. It creates a candidate; new own_pass
replay then checks it. Every subsequent result is checked before continuing. Spread<=1.25
for each measured metric and method. P2 remains untouched: a p163 retry/non-decided record
is preserved but makes this narrowly approved cost profile NOT_READY. No replacement p experiment.

B: N12/T1000/p163 CPU_MIN, SERIAL/GPU, same repeats, only if A and explicit B authorization pass.
Recheck sealed GPU correctness domain/current architecture, build and startup costs separately.
GPU startup helper uses unchanged V1; raw compiler logs and worker hello retained.

The inspector creates its own private key in a distinct process BEFORE collection; parent receives
only its public key. The inspector API accepts only stage paths for independent inspection and
next-request result checks, never arbitrary signature bodies/private key input. Controller has only
manager key. Both run under one UID: a privileged controller can replace processes or roots.
This is procedural/process separation, not adversarial OS isolation or production trust.

On receipt, manager rechecks signatures, raw evidence hashes, code/protocol and goal/session pins.
Signed count/head witness outside the manager directory detects tail deletion relative to that head;
same-account simultaneous witness rollback remains unresolved. Single serial research controller,
not concurrent production transactions. Missing/failed rollback stops new requests.

Next actual request uses immutable research snapshot -> unchanged V1 FIXED method service.
Independent inspector checks that new output against the fresh replay. Rollback signs LEGACY;
new snapshot is legacy, already-started snapshot remains pinned. No extra physics run is launched
solely for rollback; future legacy execution is the unchanged V1 path.

Report all goal-specific categories plus whole job CPU/wall and rate estimate (not billing receipt).
Five repeated measurements, replays, preparation, signing and actual learned request are charged.
Only one realized reuse is measured; future repetitions are UNCONFIRMED. Whole-job recovery is
conservatively computed separately per goal, never adds CPU savings to wall savings or multiplies
old speedups. `REAL_LEARNING_COST_USEFUL` requires realized positive whole-job net benefit.

Preserve all failures and raw evidence before shutdown. Long network loss, actual FAILED-trigger
shutdown, sampled resource caps on a real GPU session and OS key isolation remain untested until
separately demonstrated. Shared RwForce remains INDEPENDENT_FORMULA_VERIFICATION_V0 follow-up.
