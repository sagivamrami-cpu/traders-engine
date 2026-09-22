# Task 2: Source audit and final acceptance

Implement only Task 2 from
`docs/superpowers/plans/2026-09-14-lifecycle-open-minimum-success-source.md`.

Create:

- `trading_system/tree_spec/lifecycle_open_minimum_success_source.py`
- `tools/check_lifecycle_open_minimum_success_source_parity.py`
- `tests/tree_spec/test_lifecycle_open_minimum_success_source.py`

The auditor must pin retained `tracker.py` physical source lines 2690–2704,
commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`, and blob
`b616b34022e436545d8c1daf85eced51614fd74e`. It may read/parse source but
never import/execute it. Compare the exact physical branch and the Task 1
runtime against the only allowed projection. Require valid accepted child
audits for the post-fill evidence, lifecycle transitions and outcome shelf
components; all child reports must be verified, blocker-free, source-pinned,
serializable and false for both readiness flags.

The CLI takes required `--source-root`, emits valid JSON on every path and
returns exit 0 only for verified exact source projection. All failures must be
BLOCKED with `ready_for_replay=false` and `ready_for_training=false`.

TDD mutation coverage must include quote guard/order, low/high protection and
directional progress, source minimum progress mutation, message-before-outcome
ordering, source commit/blob/physical-order drift, malformed children/missing
root and malformed/serialization CLI reports.

Run the Task 1 runtime tests plus the new auditor test suite and explicit-root
CLI. Write a complete RED/GREEN/verification report to
`.superpowers/sdd/2026-09-14-lifecycle-open-minimum-success-source/task-2-report.md`.
Do not modify Task 1 production behavior unless a verified compatibility
failure requires it. Do not acquire data, add resolver/economics/replay/model
work, execute/import retained source, commit/push, alter unrelated files or
spawn subagents.
