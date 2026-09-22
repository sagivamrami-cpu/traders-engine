# Task 3 corrective revision report

## Scope

Revised only the authorized Task 3 checkpoint/context and test paths. No retained
source was accessed, imported, or executed. No runner, tracker record, delivery,
filesystem/network discovery, economic label, dataset, training, model, live
behavior, readiness-positive claim, commit, or push was added.

## Architectural API change

`ReplayProviderBaseline.capture(watch=..., admission=...)` creates the trusted
provider/source/schedule baseline while the run still owns its original supplied
providers. The caller retains that object independently and supplies it as
`baseline=` to both `checkpoint_from(...)` and `restore_checkpoint(...)`.

The checkpoint stores only the baseline fingerprint. Restore compares its
reconstructed watch identity, current provider identities, current frame image,
and exact remaining publication/lock suffixes against the independently supplied
baseline. A checksum recomputed over forged checkpoint bytes therefore cannot
replace a watch source or add/substitute future provider evidence. This is the
smallest Task 4-usable boundary; it deliberately does not pretend that a
self-contained digest authenticates attacker-recomputed input.

## Corrected invariants

- Creation and restore bind each completed ledger row by indexed pass ID,
  decision time, and the full ordered bundle event prefix available at that
  anchor.
- Creation requires `watch.source._clock is admission._clock`, not merely equal
  current clock times.
- All checkpoint and admission snapshot timestamp parsers reject ISO fractions
  longer than six digits before `datetime.fromisoformat()`, including packed
  evidence and checksum-recomputed checkpoint input.

## RED evidence

Before the implementation, the new checkpoint regression suite failed at
collection because the required trusted baseline API was absent:

```text
ImportError: cannot import name 'ReplayProviderBaseline'
```

The added cases cover a legal but wrong-anchor ledger at create/restore with
recomputed checksums; forged watch source; substituted and added future
publication/lock schedules with recomputed nested and outer checksums; distinct
but time-equal clock instances; and over-precision outer and packed timestamps.

## GREEN evidence

```text
python -B -m pytest tests/tree_replay/test_causal_replay_checkpoint.py tests/tree_replay/test_admission_context.py tests/tree_replay/test_admission_io.py tests/tree_replay/test_watch_storage.py tests/tree_replay/test_shared_clock.py -q --tb=short -p no:cacheprovider
```

Result: `181 passed in 8.66s`.

## Remaining scope

This remains Task 3 provider/checkpoint infrastructure only. `ready_for_replay`
and `ready_for_training` remain false. Task 4 must create and retain one trusted
baseline alongside its original providers, then pass it at each checkpoint and
restore boundary. Full replay execution, source-order runtime binding,
lifecycle/candidate execution, persistence/delivery, economic outcomes,
datasets, training, models, and live trading remain excluded.
