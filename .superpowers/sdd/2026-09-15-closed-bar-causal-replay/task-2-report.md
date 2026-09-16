# Task 2 implementation report: source-pinned outer-pass intake

## Changed files

- `trading_system/tree_spec/causal_replay_source.py`
- `tools/check_causal_replay_source_parity.py`
- `tests/tree_spec/test_causal_replay_source.py`
- `configs/trees/causal-replay-source-contracts.json`
- `docs/architecture/CAUSAL-REPLAY-SOURCE-INTAKE.md`
- this report

## Source handling

The retained chart-desk checkout was inspected only through local read-only
Git identity queries and text/AST parsing of `scripts/market_watch.py`. It was
not imported, compiled, or executed. Read-only pin verification found HEAD
`68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9` and the pinned source object
`f530fbe82cffbaf831c7a7725c7a9bf6143e6b8b`.

## Evidence

RED, before implementation:

```text
python -B -m pytest tests/tree_spec/test_causal_replay_source.py -q --tb=short -p no:cacheprovider
25 failed
```

The failures were the expected missing auditor module and CLI.

GREEN:

```text
python -B -m pytest tests/tree_spec/test_causal_replay_source.py -q --tb=short -p no:cacheprovider
25 passed in 3.90s

python -B tools/check_causal_replay_source_parity.py --source-root C:\Users\roeea\AppData\Local\Temp\tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
VERIFIED (exit 0)
```

The mutation suite covers source commit/blob drift; state load and both writes;
lock, lifecycle-pass, and gate ordering; level-reversal/tree/engine ordering;
all six outer gate locations; record and `--telegram` control flow; manifest
drift; malformed audit output; missing roots; and CLI exception behavior.

## Caveat

This is an audit only. Its six outer-admission gates are reported solely as
`UNWIRED_OUTER_ADMISSION`; no tracker registration, delivery, data archive,
economics, dataset, training, model, or replay runtime was added. Both
readiness flags remain false in every report.
