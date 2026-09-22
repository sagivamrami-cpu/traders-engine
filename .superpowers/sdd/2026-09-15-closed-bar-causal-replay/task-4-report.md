# Task 4 report: BLOCKED by upstream contracts outside authorized scope

## Scope attempted

Only the Task 4-authorized runner, tests, package export, and this report were
edited. The runner uses the supplied shared clock, watch store, admission
context, `TrackerLifecycleCaller`, `LifecycleClosedResolver`, and private
`_evaluate_reversal_asof`; it contains no retained-source import/execution and
does not call `TrackerAdmission.record` for a selected plan.

## RED evidence

Before the runner was created:

```text
python -B -m pytest tests/tree_replay/test_causal_replay.py -q --tb=short -p no:cacheprovider
ModuleNotFoundError: No module named 'trading_system.tree_replay.causal_replay'
```

After the Task 4 runner/test implementation, the focused suite remains RED for
two pre-existing dependency-contract defects that cannot be corrected in the
authorized Task 4 files:

1. A second `ReplayRunLedger.append()` is impossible. `append()` requires the
   new record's predecessor digest to equal `ledger.digest`, while
   `ReplayRunLedger.__post_init__()` requires that same value to equal the
   preceding record digest. Those digests are different by construction, so a
   second source pass raises `ValueError: record predecessor_digest does not
   match prior ledger`. This blocks `run()`, `run_until()`, and split-resume.
   The required correction is in
   `trading_system/tree_replay/causal_replay_contracts.py`, which is not an
   authorized write for Task 4.

2. `LifecycleClosedResolver` requires exactly
   `fetch_corrected(symbol, "15m", 3)`. `CausalAdmissionContext` accepts only
   the pinned admission-frame keys, whose 15-minute keys are 55 and 5 days;
   `15m/3` is rejected by `AdmissionFrameRequest` as unsupported. The runner
   correctly treats the absent exact lifecycle evidence as `BLOCKED` rather
   than silently substituting the five-day request. The required lifecycle
   evidence binding/contract is absent from Task 4's defined constructor and
   cannot be invented as a fallback.

The current focused result is `6 failed, 6 passed`; the multi-pass ledger and
actual OPEN lifecycle checks expose the two blockers above.

## GREEN

No GREEN claim is made. The plan's combined Task 4/dependency command cannot
pass until the two upstream contract boundaries are resolved under explicit
authorization.

## Safety boundary retained

No commit, push, subagent, source execution/import, tracker registration,
delivery, broker, economic label, dataset, training, model, or readiness claim
was made. The Task 4 private lifecycle tape is memory-only and forwards only
the supplied admission state/frame/clock ports.
