# R=0.4 CI Micro-Audit V0 evidence

Main report: [H2_R04_CI_LAYER_MICRO_AUDIT_V0.md](../H2_R04_CI_LAYER_MICRO_AUDIT_V0.md).
All physical execution records are in [evidence/](evidence/); the audit stopped
on its first determinant-action discrepancy and made no physical rerun.

- preparation_seal/execution_seal: exact base/source/input/selection binding.
- basis_mapping: all 1830 canonical state identities and two historical indices.
- matrix_elements: preselected classes with exact dyadic terms and signs.
- submatrix: preselected canonical 12×12 comparison.
- matvec/matvec_single.npz: all outputs of the first e_(50,50), later vectors STOP.
- counterexample/counterexample_reduction: raw operator agreement and three
  absorbed-K changes explaining the previous action discrepancy.
- eigensolver: NOT_EXECUTED; no eigenenergy/Pachucki comparison.
- runtime_source: actual installed PySCF source and library hashes.
- preservation: physical-run 910 byte bindings unchanged.
- report_metrics/summary: costs, limitations and classification.
- artifact_manifest: immutable compact physical records, including original
  Windows separator spellings in relative paths. Resolve separators by platform
  for reading; do not rewrite manifest bytes.

Large unchanged h.npy/g.npy remain under the attached worktree's
`runs/h2_ci_layer_audit_v0/audit_v0/`; their hashes are recorded. They were
materialized once from original sealed AO/C with the unchanged V0 transformation.

validation/: both initially failed cross-platform/environment selections and
final passing logs/JUnit; preflight/: original preparation mistakes. None is
an additional physical solver attempt. Final verification is source/fixture
preservation plus related tests, not formal certification or QZ44 PASS.

Artifact Git attributes preserve mixed LF/CRLF and pytest trace whitespace
byte-for-byte; whitespace lint treats those original record bytes as data.
The source and report still use the normal whitespace check.
