# Task 3 report — shared clock and causal-provider checkpoint

## Scope

Implemented only the approved Task 3 runtime/test paths:

- optional exact shared `ReplayClock` binding for `CausalAdmissionContext`;
- detached quote, admission-context, and checkpoint snapshots;
- canonical checkpoint/restore validation for the immutable bundle, ledger,
  shared time, watch state, and causal admission state;
- resumed provider construction exclusively through public constructors and
  existing validators.

No retained source was checked out, imported, or executed. No runner, tracker
record, delivery, filesystem/network discovery, economic label, dataset,
training, model, live behavior, readiness change, commit, or push was added.

## RED evidence

Before implementation:

```text
python -B -m pytest tests/tree_replay/test_causal_replay_checkpoint.py tests/tree_replay/test_shared_clock.py -q --tb=short -p no:cacheprovider
```

Result: collection failed as intended with
`ModuleNotFoundError: No module named 'trading_system.tree_replay.causal_replay_checkpoint'`.

## GREEN evidence

```text
python -B -m pytest tests/tree_replay/test_causal_replay_checkpoint.py tests/tree_replay/test_admission_context.py tests/tree_replay/test_admission_io.py tests/tree_replay/test_watch_storage.py tests/tree_replay/test_shared_clock.py -q --tb=short -p no:cacheprovider
```

Result: `174 passed in 4.58s`.

```text
python -B -m py_compile trading_system/tree_replay/admission_context.py trading_system/tree_replay/admission_io.py trading_system/tree_replay/watch_storage.py trading_system/tree_replay/causal_replay_checkpoint.py
```

Result: exit 0.

Focused coverage proves shared context/watch clock advancement; exact clock
binding; detached return values; changed source and valid reordered event bundle
rejection; malformed outer/inner checksums; ledger-digest mutation; and
publication/lock-step resurrection attempts. Restore rebuilds frozen seeds,
frame requests, publications, and lock steps through their normal constructors.

## Concerns and limits

This is provider/checkpoint infrastructure only. A checkpoint is legal only
when its remaining lock evidence has not already started; that fail-closed rule
prevents a resumed pass from replaying an unconsumed past lock operation.
The snapshot checksum detects mutation but is an integrity digest, not a secret
or authorization mechanism. Full pass execution, source-order binding at
runtime, lifecycle resolution, candidate observation, and all economic/data/
model work remain Task 4+ and are intentionally absent.
