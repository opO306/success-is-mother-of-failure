# C1-B1 Candidate B promotion plan

**Goal:** Validate the existing Pilot B as a separate opt-in impulse fast-path candidate.
**Spec:** User attachment a25782a8-98a7-429d-abcc-923044740f43; instructions 1–16.
**Architecture:** Preserve all slow reference bytes. Import the exact Pilot A/B and independent checker into an isolated package. Bind new subprocess evidence to one run, source inventory and immutable dataset. Integrate B through a separate step entry point only after independent audit.
**Tech stack:** Python integers/Fraction, pytest -n 6, local CPU.

## Constraints and review focus

- No push, H2, foundation, physics/parameter/domain/rounding/cap/GPU changes or candidate search.
- Missing/stale/mixed evidence must never PASS; failure artifacts remain.
- Denominator positivity, all multiplication sign branches, EXP endpoint identity, exact inverse powers, exact sqrt enclosure.
- Preserve domain, overflow and precision STOP, including zero dt and opposite-sign endpoint overflow.
- Endpoint equality is distinct from trajectory equality and formal certification.
- One final local commit; no default-path activation before all promotion gates.

## Ordered tasks

- [x] Evidence closure: new run_pilot.py, evidence.py, stage.py, tests/test_c1b1_candidate_b.py. Persist REF/A/B/checker endpoints and actual decision sequences, input and source hashes; test stale/missing/source/input/rc/output corruption.
- [x] Independent audit: reviewer examines Pilot primitives and live AST composition after closure; positive denominator guard and regression of rejected reciprocal recurrence. Preserve audit findings.
- [x] Integration: a_reference/c1b1_fast_impulse.py opt-in impulse/step; original _model_R, impulse, step and energy paths remain byte-identical. Differential gate first.
- [x] LOCAL FULL: python -m pytest tests -q -n 6; log/JUnit, true skip separate from strict xfail, do not update AGENTS baseline.
- [x] Trajectory differential: same raw initial state, compare every impulse and stored state, domain/overflow/refused step; persist witnesses.
- [x] Performance: same local CPU, one thread, warm-up, alternating REF/FAST repetitions and medians for kernel, step and whole trajectories.
- [x] Promotion: independently check all stage records, document gaps and status, diff review, one local commit, final Git state.

## Execution ledger

Start HEAD/origin: 6c53eec71e981cef35f850095da76b965457866c, clean, 0/0.
Ruling: user supplied complete execution scope; implement continuously without a second plan approval. Work on local codex branch, preserve historical Pilot downloads and runs. Branch remains in same checkout to use local native/GPU/reference environment.
Mandatory documents read; memory registry queried with no relevant hit (no memory facts used).
Four Pilot reference blobs match current Git. Existing summary hardcodes PASS and combines old JSON.

Final source audit: independent candidate_b_audit reviewer, 21 reviewed files pinned.
Shared-root H2 writes caused two source-bound test interruptions; isolated native managed worktree created at same start HEAD.
Git checkout newline variants independently audited. FULL v2: 3711 passed, 2 missing historical artifact failures, 1 strict xfail, 25 warnings / 699.86s.
Restored only sealed assets/sources (newline-only existing differences), 191 files; failed tests 2 passed / 16.60s.
Fresh final v3 run_id 3e404fde-e116-4248-ba00-7d78c6244f2f, source c3534d1a2437d7d0fe0b6fb12cd7ba93d29e76bd66c8bf06ea0bad287c82dc87.
10 stage returncodes zero; final promotion PASS. LOCAL FULL 3713 passed + 1 strict xfail, actual skip/failure/error 0 / 774.77s, 25 unresolved warnings.
Three scattering trajectories 34305 steps, total 34312 impulses including four refusal fixtures; all raw states/results agree.
Single CPU affinity 11, warm-up1, repeat3: CPU median impulse1.880x, step1.475x, complete finite trajectory1.400761x; CPU reduction28.61%.
Production fast-path candidate, reference/default/world certification states preserved; no push.
