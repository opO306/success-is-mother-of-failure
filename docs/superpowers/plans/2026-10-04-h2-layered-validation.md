# H₂ Multi-Step Layered Validation Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Native implementation in this existing Pilot worktree; one fresh whole-change review at the end.

**Goal:** Execute exactly five additional Velocity Verlet steps from sealed C0 with Quick checks each step, two center diagnostics, and start/end provenance audits.

**Architecture:** Keep electronic kernels and previous evidence byte-identical. Copy actual Python runtime sources, raw basis/config, mass and sealed protocol to an exclusive campaign snapshot; launch controller/workers in isolated Python mode from that snapshot. States remain SPECULATIVE until final full audit and scalar-chain replay; any failure retains C0 and marks descendants DISCARDED without deletion or automatic rerun.

**Tech Stack:** Existing WSL PySCF/SciPy binary64 environment; Decimal80 integrator; independent Fraction checker; GNU time and 20ms sampled workflow RSS.

**Spec:** `C:/Users/zun24/.codex/attachments/81b4259e-78a0-4a22-a201-1c373d360a4d/붙여넣은 텍스트.txt` (read in full).

## Global Constraints

- C0 is accepted prior R1/P1/F1, reused with no fresh F1 calculation.
- Additional steps=5; dt=1, h=.1, μ=mp/2; cc-pV5Z/full-CI, unchanged guards; Decimal80.
- Two stencil energies per step; center energy only at additional steps3 and5, total new calls12.
- Quick: finite, center R in[1.2,1.6], guards, geometry rounding, force/equation recomputation, COM/p sum, state hash.
- Full provenance only start/end; early hard failure escalates immediately and stops. No retry.
- H/K/ΔH diagnostics MEASURED only; no physical drift tolerance.
- K=1/5/10/50/100 models only, no chosen cadence; NOT CERTIFIED/NOT PRODUCTION APPROVED.
- No modification of original calculator/common/frozen code; no optimization branch, merge/rebase/push.
- Related tests replace LOCAL FULL only under repository's new independent Pilot exception; baseline unchanged.

## Review Focus

- Final audit mismatch must retain exactly C0, discard all later states and preserve raw evidence.
- Snapshot imports must come from the snapshot, not checkout/PYTHONPATH; external numerical libraries remain a disclosed trust base.
- Force carry reuse and per-step/center call counts must be real runtime receipts, not inferred from planned counts.
- NaN/Inf/REFUSED, domain exit, COM/momentum and geometry corruption must stop before another step.
- Medium diagnostics do not promote C3; no arbitrary ΔH tolerance; cost clock scopes must not overlap or hide setup.

### Task 1: Scalar and validation/promotion semantics

Create `electronic_pilot/h2_multistep_v0/{scalar,kit}.py`; tests `tests/h2_multistep_v0/test_kit.py`.
Consumes C0/state dict(R,P,F), old immutable electronic contract/geometry helpers. Produces `drift(previous,mass)`, `finish(previous,half,left,right,mass)`, `quick(previous,step,mass,snapshot_root)`, `decide(c0,steps,audit_ok,quick_ok)` and `cadence(cost)`.
- [ ] Write/rerun tests: exact quadratic update; force carry; all guard/finite/domain/COM/geometry/hash faults; refused diagnostics; rollback/final promotion; independent scalar replay; no ΔH tolerance.
- [ ] Observe missing-feature failures, implement, run new tests and prior 130 related tests.

### Task 2: Snapshot and measured campaign

Create `{campaign,worker,launch}.py`. Snapshot packages/config and protocol/seal under exclusive raw campaign folder. Controller uses snapshot imports; original numerical kernels are copied byte-for-byte. Historical hash set includes prior seals/raw/source, excluding mutable dashboard snapshots.
- [ ] Tests for snapshot mutation and wrong module origin, start/end hash checks, state persistence faults and retained C0.
- [ ] Seal protocol/implementation/preflight before new energies; verify runtime and old state once at start.
- [ ] Execute five steps once; save each process time/RSS, Quick time and state/hash; center diagnostics at3/5.
- [ ] Final full audit includes all recorded state/point hashes and independent chain replay, then promote or discard; STOP.

### Task 3: Evidence, cost and final review

Create `docs/active/h2_multistep_layered_v0/` report/captures/seals and post-acquisition capture tests; update CURRENT_STATE/REPO_MAP/verification lessons only after end audit.
- [ ] Run capture+related tests after campaign and evidence writing finishes; preserve all initial failures.
- [ ] Report raw dynamics/Quick/Medium/final diagnostic/full-start/full-end/setup costs, historical comparison, K models and rollback exposure. No universal safety claim.
- [ ] Check spec alignment separately, review complete change with fresh reviewer, fix actual material findings with bounded tests.
- [ ] Seal stable final evidence, commit locally, verify clean tree/root master/remote heads unchanged; no push.
