# Explicitly approved remote CPU-only verification

Do not run locally. Do not start an instance, install dependencies, run physics or CUDA.
Preparation commands, reads, hashes and Git commits do not execute the new modules.

1. User approves this gate and starts an exclusive instance. Use the supplied SSH address.
2. Administrative control verifies exact instance, current hourly price <= $0.25,
   patched V0 external_guardian.ps1 hash, existing DEADLINE/COMPLETED stop evidence.
   Long network failure / actual FAILED stop are still unverified.
3. Check approved runtime has pytest and cryptography; absent dependency => STOP, no install.
4. Transfer byte-preserving sealed ZIP; verify archive hash before extraction into new directory.
5. Prepare explicit OFFLINE_ONLY authorization with gate, instance_id,
   explicit_user_approval=true, approval_reference, code_seal_sha256,
   new_trajectories=0 and gpu_calls=0. This gate's preparation is not execution approval.
6. Arm the pinned V0 external guardian on the outside control host with a dedicated
   authorization, exclusive instance, completion marker and <= 600s deadline.
   Verify ARMED receipt BEFORE execution. Container-side CPU/wall limit is 120s.
7. Run approved existing Python runtime (for earlier instance: /workspace/ae1/venv/bin/python):

```
python -m experiments.adaptive_execution_learning_v1.offline --authorization AUTH.json --code-seal-sha256 PIN --out NEW_OUTPUT
```

8. On success/failure collect output, preserving failures, and signal guardian COMPLETED/FAILED.
   Confirm actual exited/stopped via a separate API read; a stop request alone is insufficient.
   Guardian deadline remains armed if SSH/completion signalling fails.
9. Total budget $0.10, allocated <=10min at <=$0.25/hr; current billing cannot be assumed.
   At most 3 approved attempts; no automatic escalation or numerical next stage.
10. Archive raw observations, receipts, public roots, profiles, approval events, refusals,
    JUnit, runtime, timings and shutdown evidence. Never export the ephemeral test private keys.

Cryptography's maintained Ed25519 signing/verification is used; no custom crypto:
https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/
All issued keys/approvals in this demo are TEST_ONLY. Operational issuers do not exist here.
