# Codex acceptance — tracker lifecycle caller Task 1

Request: `docs/superpowers/plans/2026-09-14-tracker-lifecycle-caller-source.md`,
Task 1.

Status: **ACCEPTED_BY_CODEX**.

The offline caller seam in `trading_system/tree_replay/lifecycle_caller.py`
loads once, has no effects for empty/unchanged passes, and on actual change
orders lifecycle gate persistence before tracker save. Its live wrapper uses
the source context's shared lock policy; a nested context proves no second
acquire. It preserves the source's broad `LockBusy` catch, now explicitly
documented and regression-tested.

Independent evidence: normal missing-module RED (12 failures); final focused
runtime/consumer proof:

```text
python -m pytest -q tests/tree_replay/test_lifecycle_caller.py tests/tree_replay/test_lifecycle_gate.py tests/tree_replay/test_tracker_lock.py tests/tree_replay/test_tracker_storage.py
113 passed in 0.87s
```

Task review initially found the unshared-lock defect; it was fixed, then
scoped re-review returned PASS with no findings. This is caller sequencing
only, not source mutation bodies, parked replay caller context, delivery,
full replay, execution/economics, labels, dataset or training readiness.
