# Task 4 ledger-chain root-cause fix report

## Scope

Changed only the causal replay ledger contract and its focused contract test.
No runner, checkpoint, retained-source, tracker, delivery, economic, dataset,
training, model, or readiness behavior changed.

## Root cause

`ReplayRunLedger.__post_init__()` validates every non-initial record against the
previous `ReplayPassRecord.digest`, while `append()` incorrectly required the
aggregate `ReplayRunLedger.digest`. Those values differ after the first record,
making a correctly chained second append impossible.

## RED

Added a real two-record append regression that gives the second record the
first record's digest and separately proves that the aggregate ledger digest is
not an acceptable substitute. Before the fix:

```text
python -B -m pytest tests/tree_replay/test_causal_replay_contracts.py -q --tb=short -p no:cacheprovider
1 failed, 53 passed
ValueError: record predecessor_digest does not match ledger
```

## GREEN

`ReplayRunLedger.next_predecessor_digest` now returns genesis (`ledger.digest`)
for an empty ledger and the previous record digest otherwise. `append()` uses
that value; the aggregate ledger digest calculation is unchanged.

```text
python -B -m pytest tests/tree_replay/test_causal_replay_contracts.py -q --tb=short -p no:cacheprovider
54 passed
```

## Task 3 compatibility

The initial-record genesis value remains `ledger.digest`. Ledger serialization
and aggregate digest computation are unchanged, so Task 3 checkpoint identity
and prefix-validation semantics are preserved.
