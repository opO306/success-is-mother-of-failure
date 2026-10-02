# C1-B1 mainline merge and runtime activation

Authority: human request in this chat, 2026-10-02, seven ordered phases; no push.
Start master/origin: 6c53eec71e981cef35f850095da76b965457866c.
Candidate: 951b07695e74abc633168ddb672b11e2289184c9.

## Constraints

- Preserve slow reference, generic model, energy/potential, proof/checker dependencies,
  physical parameters, domain, rounding, precision cap and old evidence.
- No activation before master FULL plus source/closure checks pass.
- Default production runtime may use FAST; explicit reference mode remains available.
- Differences stop the gate. No silent retry or replacement of failed evidence.
- Master is explicitly authorized; do not create a merge commit or push.

## Tasks and ledger

1. [x] Inspect clean Git and fetch; reset master to origin; fast-forward candidate.
   Actual master HEAD 951b076..., no merge commit. Reviewed source inventory restored
   solely for newline differences; all Git source blobs unchanged.
2. [x] Fresh master closure/audit and LOCAL FULL; verify source/step/refusal independence.
   3713 passed + 1 strict xfailed, fail/error/actual skip 0, 25 warnings;
   pytest 717.36s / subprocess wall 718.871749s. Closure/source checks PASS.
3. [x] RED tests for real producer dispatch, default fast and explicit reference mode;
   implement runtime selection at production producer call site.
   22 RED missing selector/gate -> 22 GREEN. Fabricated median RED -> GREEN.
   Independent reviewer: Critical 0 / Important 1 (history validation completeness).
   Final fix pass: six origin/history faults RED -> GREEN; also reject changed
   refusal state and accept the intact structural fixture. No runtime math changed.
4. [x] Seal original three plus extra representative trajectories and refusals;
   compare actual selected runtime impulses/stored states/final states/STOP steps.
   55,845 successful steps, 55,856 impulse calls including five refused attempts.
   Actual producer retained-input REF/FAST execution also matched all 1491 steps.
5. [x] Fresh post-activation LOCAL FULL; no omission.
   3744 passed + 1 strict xfailed, fail/error/actual skip0, warnings25;
   pytest702.25s / subprocess wall703.739897s.
6. [x] Remeasure impulse/step/trajectory: one CPU, warmup, repetitions, median,
   source/input fingerprints, repeat equality; comparable old-three subtotal.
   CPU speedups impulse1.600 / step1.410256 / old3trajectory1.384513 / all6 1.409504.
7. [x] Profile complete FAST trajectories; exclusive CPU top five, calls/per-call,
   exactness, duplicate-work bounds, Amdahl upper limits; no next-target selection.
   Profile233.796875 CPU s; pstats-derived exclusive top5 reproduced. Source-based
   duplication interpretation stored separately, original profile unchanged.
8. [x] Fresh independent whole-change review, documentation, local commit, final Git.
   Independent Critical0/Important1 fixed with RED->GREEN and fresh full suite.
   Final code/source/input checks PASS. Commit and Git state recorded at completion.

Final Rulings: declined legacy full-candidate mathematical proof, A-wide physical
closure and formal verification remain outside this activation task. Integration
equality cannot compensate for an incorrect old mathematical premise.
No next optimization target selected. Deferred minors: none from the reviewer.
Manual imported-checker inspection refused huge diagnostic rationals under default
4300 text-digit limit; retained, then PASS with CLI-equivalent diagnostic setting.
No production precision cap or ordinary dt40 runtime setting changed.

Pre-flight shared interfaces: all fresh stages pin the same immutable source inventory.
Activation necessarily invalidates live comparison with the pre-activation inventory;
retain pre-activation run, seal a new post-activation run, and rerun closure on it.
Historical O-1 producer and witness/proof wrapper stay source-pinned and use slow REF.
Actual production replay producer dispatch is the intended activation call site.
Review focus: no fallback hiding mismatches; no altered REF/proof/checker; actual
production producer uses the selector; cache reuse and refusal preserve state;
profiling percentages exclusive, inclusive maxima not additive; paths portable.
