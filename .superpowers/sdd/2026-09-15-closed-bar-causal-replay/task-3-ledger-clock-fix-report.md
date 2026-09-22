# Task 3 C1 ledger-clock correction report

## Scope

Implemented only the final Task 3 C1 correction in the authorized checkpoint
module and checkpoint tests. No retained source was read, imported, or
executed. No subagent, commit, runner, provider schedule API, delivery,
economic outcome, dataset, training, model, or readiness behavior was added.

## Correction

`checkpoint_from()` and `restore_checkpoint()` now reject a nonempty consumed
ledger when the shared checkpoint clock precedes the final consumed immutable
bundle anchor. The comparison is made after the existing indexed ledger-prefix
validation and uses `bundle.anchors[index - 1].decision_time`; empty ledgers
remain unaffected.

The existing combined consumed-provider-evidence chronology test was split so
that each baseline predicate is independently exercised:

- a publication-only consumed schedule backdated after the completed ledger
  anchor but before its publication; and
- a lock-only consumed schedule backdated after the completed ledger anchor but
  before its lock step.

Both cases first restore the legal checkpoint successfully, then recompute the
nested and outer checksums after the backdate and reject through the provider
baseline guard. The C1 factory and checksum-recomputed restore regressions use
no provider publications or lock steps, so their failures cannot be masked by
either provider-schedule predicate.

## RED evidence

Before the correction:

```text
python -B -m pytest tests/tree_replay/test_causal_replay_checkpoint.py -q --tb=short -p no:cacheprovider
2 failed, 15 passed in 12.91s
```

The two intended C1 tests failed because neither checkpoint creation nor restore
raised for a clock at `T` with an already-consumed anchor/ledger record at
`T + 1 second`.

## GREEN evidence

After the correction:

```text
python -B -m pytest tests/tree_replay/test_causal_replay_checkpoint.py -q --tb=short -p no:cacheprovider
17 passed in 11.08s

python -B -m pytest tests/tree_replay/test_causal_replay_checkpoint.py tests/tree_replay/test_admission_context.py tests/tree_replay/test_admission_io.py tests/tree_replay/test_watch_storage.py tests/tree_replay/test_shared_clock.py -q --tb=short -p no:cacheprovider
187 passed in 20.89s
```

## Remaining scope

This closes only the Task 3 C1 checkpoint-clock boundary. The component remains
offline supplied-evidence infrastructure; it does not establish replay runner,
causal feed, lifecycle execution, persistence/delivery, economics, dataset,
training, model, or live-trading readiness.
