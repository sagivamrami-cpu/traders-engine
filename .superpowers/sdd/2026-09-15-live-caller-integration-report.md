# Live caller / resolver integration test report

## Scope

Test-only proof that `TrackerLifecycleCaller.check_live` composes the existing
`LifecycleLiveResolver(source).resolve` over one explicit offline source. No
production module, source pin, auditor, documentation, or readiness claim was
changed.

## RED

Before the test file existed, ran:

```text
python -m pytest -q tests\\tree_replay\\test_lifecycle_live_caller_integration.py
ERROR: file or directory not found: tests\\tree_replay\\test_lifecycle_live_caller_integration.py
no tests ran in 0.00s
```

The failure was the intended missing-test-file RED evidence. The production
caller and resolver were already present; this task adds no production code.

## GREEN evidence

After adding the test file, ran:

```text
python -m pytest -q tests\\tree_replay\\test_lifecycle_live_caller_integration.py
3 passed in 0.57s
```

Then ran the direct caller/resolver regressions:

```text
python -m pytest -q tests\\tree_replay\\test_lifecycle_live_caller_integration.py tests\\tree_replay\\test_lifecycle_caller.py tests\\tree_replay\\test_lifecycle_live_resolver.py
34 passed in 0.64s
```

The checks prove:

- unchanged resolver result: lock/load/two quote reads/resolver branch/release;
  no gate or save;
- changed `PENDING -> OPEN`: the real caller gates then saves the real resolver
  output and the transitioned state before releasing the lock;
- `LockBusy`: no load, quote read, resolver branch, gate, save, or state change.
