# Task 4 lifecycle frame-contract root fix

## Scope

Only the explicit `15m`/`3` admission-frame request identity, its focused
contract test, and this report changed. No fallback, alias, inferred lookback,
or lifecycle-resolver behavior was added or altered.

## Root cause

`LifecycleClosedResolver` requests
`fetch_corrected(symbol, "15m", 3)`. `AdmissionFrameRequest` and
`AdmissionFrameSource.fetch_corrected()` both validate their identities against
the same `_REQUEST_KEYS` set, which previously omitted `("15m", 3)`.

## RED

Before the production change:

```text
python -B -m pytest tests/tree_replay/test_admission_frames.py -q --tb=short -p no:cacheprovider -k exact_lifecycle_m15_three_day_frame_is_accepted_and_fetched
1 failed, 41 deselected
ValueError: unsupported original admission timeframe/lookback pair
```

The new test constructs supplied exact `15m`/`3` causal evidence and fetches
that same identity through the real `AdmissionFrameSource` boundary.

## GREEN

After adding only `("15m", 3)` to `_REQUEST_KEYS`:

```text
python -B -m pytest tests/tree_replay/test_admission_frames.py -q --tb=short -p no:cacheprovider -k exact_lifecycle_m15_three_day_frame_is_accepted_and_fetched
1 passed, 41 deselected

python -B -m pytest tests/tree_replay/test_admission_frames.py -q --tb=short -p no:cacheprovider
42 passed in 2.30s
```

## Boundary retained

The new identity accepts only caller-supplied exact causal evidence. It does
not fetch market data, substitute another request, alter frame trimming or
correction semantics, or assert replay, economic, dataset, model, or trading
readiness.
