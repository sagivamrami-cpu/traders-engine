# Task 1 Revision Report

## Changed files

- `trading_system/tree_replay/causal_replay_contracts.py`
- `tests/tree_replay/test_causal_replay_contracts.py`

No retained source was imported or executed. No tracker, delivery, network,
filesystem, economic, data/model, or readiness behavior was added.

## RED/GREEN evidence

RED (after adding the regression tests, before production changes):

```text
python -B -m pytest tests/tree_replay/test_causal_replay_contracts.py -q --tb=short -p no:cacheprovider
25 failed, 28 passed in 0.38s
```

The failing cases were the seven-digit serialized payload timestamp and all
nested forbidden-field combinations for `ReplayEvent.payload` and
`ReplayPassRecord.diagnostics`. The candidate combinations were already
protected by the pre-existing recursive candidate guard.

GREEN:

```text
python -B -m pytest tests/tree_replay/test_causal_replay_contracts.py -q --tb=short -p no:cacheprovider
53 passed in 0.14s

python -B -m py_compile trading_system/tree_replay/causal_replay_contracts.py tests/tree_replay/test_causal_replay_contracts.py
exit 0
```

## Self-review

- A shared recursive guard now rejects the exact forbidden keys `net_pnl`,
  `net_R`, `success`, and `failure` in canonicalized payload, candidate, and
  diagnostics data, including nested dictionaries, lists, and tuples.
- Serialized payload availability rejects fractional components longer than six
  digits before `datetime.fromisoformat()` can truncate them. The regression
  also retains an accepted six-digit `Z`-timezone timestamp.
- The focused tests exercise every forbidden key across all three structured
  surfaces and all requested nesting forms. The patch is limited to the stated
  Task 1 contract boundary.
