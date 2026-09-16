# Task 3 I2 checkpoint chronology correction

## Scope

Modified only the authorized Task 3 checkpoint implementation and checkpoint
regression test. No retained source was imported or executed. No runner,
tracker record, delivery, economic label, dataset, training, model, live
behavior, readiness claim, commit, or push was added.

## Root cause and correction

Trusted baseline matching derived consumed publications and lock steps from the
remaining exact suffixes, but did not compare the omitted prefixes with the
restored decision time. A checksum-recomputed checkpoint could therefore retain
the trusted post-publication provider image while backdating its outer clock,
admission snapshot clock, and watch clock before the publication.

`ReplayProviderBaseline._matches_checkpoint()` now receives the already
validated restored decision time. After retaining the existing exact suffix
checks, it rejects a checkpoint when any consumed publication has
`available_at` after that time, or when any consumed lock step starts or
completes after it. Existing provider identity, expected-image, suffix, ledger,
checksum, and shared-clock protections remain unchanged.

## RED evidence

Before the runtime correction, the new checksum-recomputed regression consumed
a future tracker publication and a future lock sequence, backdated the outer,
admission, and watch clock fields, recomputed both nested and outer checksums,
and restored successfully:

```text
python -B -m pytest tests/tree_replay/test_causal_replay_checkpoint.py::test_restore_rejects_checksum_recomputed_backdate_before_consumed_provider_evidence -q --tb=short -p no:cacheprovider
1 failed: DID NOT RAISE <class 'ValueError'>
```

## GREEN evidence

After the chronology check:

```text
python -B -m pytest tests/tree_replay/test_causal_replay_checkpoint.py::test_restore_rejects_checksum_recomputed_backdate_before_consumed_provider_evidence -q --tb=short -p no:cacheprovider
1 passed in 0.95s
```

Required five-suite Task 3 verification:

```text
python -B -m pytest tests/tree_replay/test_causal_replay_checkpoint.py tests/tree_replay/test_admission_context.py tests/tree_replay/test_admission_io.py tests/tree_replay/test_watch_storage.py tests/tree_replay/test_shared_clock.py -q --tb=short -p no:cacheprovider
184 passed in 18.90s
```
