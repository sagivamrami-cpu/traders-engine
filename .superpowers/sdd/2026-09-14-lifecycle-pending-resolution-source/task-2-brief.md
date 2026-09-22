# Task 2 brief — PENDING branch source audit

Read first: Task 2 in
`docs/superpowers/plans/2026-09-14-lifecycle-pending-resolution-source.md` and
the binding intake
`docs/architecture/LIFECYCLE-PENDING-RESOLUTION-SOURCE-INTAKE.md`.

Implement only Task 2 files named there, plus its report at
`.superpowers/sdd/2026-09-14-lifecycle-pending-resolution-source/task-2-report.md`.
Use TDD. Read/parse but never import/execute the pinned chart-desk source.
The auditor must extract the exact source PENDING branch, transform only its
allowed offline dependencies, and compare it fail-closed to
`LifecyclePendingResolution`. Its CLI must require `--source-root`, print
valid JSON on every error, return zero only for verified source parity, and
keep both readiness flags false even when verified. It must include/require
the accepted child proofs it actually composes.

No runtime resolver modification, source change, raw market data, external
write, commit, push, or subagent is allowed. At end run focused runtime/source
suites and CLI against the retained root. Report RED/GREEN evidence, files,
auditor dependencies, blockers and concerns using apply_patch; return status,
one-line result and report path only.
