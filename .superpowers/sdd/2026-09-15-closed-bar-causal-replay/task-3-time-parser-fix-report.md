# Task 3 I1 basic-ISO precision-guard correction

## Scope

Modified only the two Task 3 timestamp deserializers and their authorized
checkpoint/admission-context regression tests. No retained source was accessed,
imported, or executed. No runner, tracker record, delivery, filesystem/network
discovery, economic label, dataset, training, model, live behavior, readiness
claim, commit, or push was added.

## Root cause and correction

Both precision guards only recognized extended ISO timestamps, allowing Python
to silently truncate the seventh fractional digit in valid basic forms such as
`20260909T160100.0000000+0000`. The guards now recognize either basic or
extended date/time separators before parsing, while retaining the existing
six-digit-or-fewer acceptance boundary.

## RED evidence

Before the runtime change:

```text
python -B -m pytest tests/tree_replay/test_causal_replay_checkpoint.py::test_restore_rejects_checksum_recomputed_basic_submicrosecond_checkpoint_timestamp tests/tree_replay/test_admission_context.py::test_snapshot_restore_rejects_checksum_recomputed_packed_basic_submicrosecond_timestamp -q --tb=short -p no:cacheprovider
```

Result: `2 failed`; neither checksum-recomputed basic ISO input raised the
required `ValueError`.

## GREEN evidence

The two focused regressions passed after the guard correction:

```text
2 passed in 1.75s
```

The required Task 3 five-suite verification also passed:

```text
python -B -m pytest tests/tree_replay/test_causal_replay_checkpoint.py tests/tree_replay/test_admission_context.py tests/tree_replay/test_admission_io.py tests/tree_replay/test_watch_storage.py tests/tree_replay/test_shared_clock.py -q --tb=short -p no:cacheprovider
183 passed in 17.39s
```

## Regression coverage

- Outer checkpoint: checksum-recomputed basic ISO `watch.covered_through` now
  rejects seven fractional digits.
- Packed admission snapshot: checksum-recomputed basic ISO quote
  `covered_through` now rejects seven fractional digits.
- Existing extended-ISO over-precision tests remain in place.
