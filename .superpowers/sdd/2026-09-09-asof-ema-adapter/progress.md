# SDD ledger — plan: docs/superpowers/plans/2026-09-09-asof-ema-adapter.md

Existing branch plan/tree-to-trained-model-langgraph; current user work preserved.
Approved architecture continuation; preflight table and explicit scope in plan.
Task 1: delegated bar boundary; parent owns separate calculation/adapter task.
Task 2: pending RED tests, pinned numerical subset, typed observations and parity.
Task 3: pending verification/review/handoff. No commits or cleanup in this slice.

Task 1 review approved original contract. Parent integration repro found that
pandas Timestamp at freshness+1ns was accepted because integer microseconds
dropped the remainder. Task1 fix requested: explicit microsecond precision
boundary, aligned subclasses normalized to native UTC; finer inputs rejected.
This is a technical input-range restriction, not a trading-time allowance.
If later feed integration needs nanoseconds, expand this contract before use.

Initial baseline:349 tree-spec tests passed in41.77s before implementation.
Task2 complete: independent spec/quality review approved with no findings;
focused32passed and actual pinned-source CLI verified function/constant ASTs and
all source blob identities, without executing source checkout code.
Task1 precisionfix: worker RED23failed138passed, GREEN161passed; scoped re-review
requested. Parent fresh combined suite542passed in39.01s. Broad run in progress.
Final review: dispatched combined current code/tests/source mapping/usage package.

Task1 complete: scoped timestampfix re-review approved; no findings.
Task3 verification: broad922passed in109.46s with legacyvalidatorfiles excluded;
combined542passed in39.01s. Removed two EOFblanklines fromvendorfiles (AST
unchanged); reran32EMA/parityfixturetests passed in1.44s plus actualsource CLI
againverified. Per-taskreview gates closed, finalcombinedreviewpending.
Keep-as-is integration preference remains: no merge/push/commit or deletion.

Final review approved integration; one minor verifier gap: empty manifest files
could vacuously verify. Controller chose to close it before handoff. Single
bounded final fix delegated for exact required file/symbol coverage and tests;
new checks must not execute source or change EMA/bar behavior.

FINAL: Tasks 1, 2 and 3 complete and accepted for the bounded local slice.
Coverage guard RED46failed/34passed, GREEN80passed; independent final scoped
re-review approved with no remaining findings. Parent inspected final code/diff
and independently verified combined590passed in20.71s, broad970passed in72.75s
(legacy validator exclusions unchanged), plus actual pinned-source CLI exit0.
Replay/training readiness remains false. Acceptance is recorded in
agent-exchange/status/2026-09-09T082710Z-codex-asof-ema-adapter.md.
No commits, pushes, merge, worktree creation or cleanup performed.
