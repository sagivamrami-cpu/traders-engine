# Task 4 revision report — runner/test failures

## Scope

Changed only the authorized Task 4 runner and tests:

- `trading_system/tree_replay/causal_replay.py`
- `tests/tree_replay/test_causal_replay.py`
- this report

No retained source was imported or executed. No subagents, commits, tracker
recording, new trade, delivery, economic, data, model, or readiness path was
added or used.

## Root causes and corrections

1. `_append()` passed the aggregate `ReplayRunLedger.digest` as every record's
   predecessor. The accepted ledger contract instead requires genesis for the
   first row and the prior *record* digest thereafter. `_append()` now uses
   `ReplayRunLedger.next_predecessor_digest`.
2. The seeded OPEN regression supplied `15m`/`5`, while
   `LifecycleClosedResolver` requires supplied `15m`/`3` evidence. The test
   now supplies that exact accepted request identity and observes the resulting
   conservative stop transition.
3. The disabled/future-activation test monkeypatched the producer to return
   `NO_CANDIDATE` while expecting selected-plan behavior. It now supplies a
   detached selected-plan report and proves activation remains diagnostic-only:
   the candidate is `OBSERVE_ONLY` for both states. Unknown variants remain
   independently `UNSUPPORTED` before producer evaluation.
4. The watch assertion omitted real `load()` internals (`exists`, `read_text`)
   while asserting the full raw trace. It now projects the high-level source
   order (`load`, pre-producer save, final save) and still proves one directory
   ensure plus both required text writes.

## TDD evidence

After test updates and before the runner edit:

```text
python -B -m pytest tests/tree_replay/test_causal_replay.py -q --tb=short -p no:cacheprovider
2 failed, 10 passed
ValueError: record predecessor_digest does not match ledger
```

The two remaining failures were the multi-pass and split/resume paths, both
caused by `_append()` supplying the aggregate ledger digest. After the one-line
runner correction:

```text
python -B -m pytest tests/tree_replay/test_causal_replay.py -q --tb=short -p no:cacheprovider
12 passed in 2.19s
```

Required Task 4 dependency verification:

```text
python -B -m pytest tests/tree_replay/test_causal_replay.py tests/tree_replay/test_causal_replay_contracts.py tests/tree_replay/test_causal_replay_checkpoint.py tests/tree_replay/test_lifecycle_closed_resolver.py tests/tree_replay/test_reversal_producer.py -q --tb=short -p no:cacheprovider
168 passed in 10.54s
```

`git diff --check` was clean for the authorized paths.

## Boundary retained

The runner still only appends detached observations and supplied lifecycle
messages. It does not call `TrackerAdmission.record` for a selected plan, and
all existing no-delivery, no-economic, no-dataset, no-training, no-model and
false-readiness boundaries remain unchanged.
