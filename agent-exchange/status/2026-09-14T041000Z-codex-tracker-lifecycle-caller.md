# Codex final acceptance — tracker lifecycle caller source seam

Plan: `docs/superpowers/plans/2026-09-14-tracker-lifecycle-caller-source.md`.

Status: **ACCEPTED_BY_CODEX**.

The accepted offline `TrackerLifecycleCaller` preserves the pinned tracker
source's changed-only end-of-pass order: resolve/mutate → lifecycle gate and
journal persistence → tracker save. Empty and unchanged state have no commit
effects. The live wrapper uses the source context's shared reentrant lock and
retains the public broad `LockBusy` return-`[]` boundary.

The independent auditor pins chart-desk commit
`68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9` and tracker blob
`b616b34022e436545d8c1daf85eced51614fd74e`; it checks both closed/live source
tails, public wrapper, runtime AST, actual lifecycle-gate/park and tracker-lock
child audits, child identity and fail-closed paths. It reads/parses retained
source only.

Final evidence:

```text
python -m pytest -q tests/tree_replay/test_lifecycle_caller.py tests/tree_spec/test_tracker_lifecycle_caller_source.py tests/tree_spec/test_lifecycle_gate_park_source.py tests/tree_spec/test_tracker_lock_source.py
70 passed in 74.94s
python tools/check_tracker_lifecycle_caller_source_parity.py --source-root <retained-root>
VERIFIED; blockers=[]
```

Task and combined final reviews are PASS. Both replay/training readiness flags
remain false. This is not resolver-body parity, parked replay context,
transport/delivery, fills/economics, replay, labels, dataset or model work.
