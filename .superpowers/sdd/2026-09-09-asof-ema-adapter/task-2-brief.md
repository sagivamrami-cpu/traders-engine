## Task 2: Pinned numerical subset and typed adapter (parent critical path)

Files: `trading_system/tree_replay/__init__.py`, `_vendor/__init__.py`, `_vendor/indicators.py`, `_vendor/tr.py`, `ema.py`; `configs/trees/ema-feature-contracts.json`; `tests/tree_replay/test_ema.py`; `tools/check_ema_source_parity.py`.

Interface:

```python
def ema_snapshot(bars, *, snapshot_id, instrument, timeframe, decision_time,
                 history_start, max_age_seconds) -> dict:
    ...
```

- [ ] Before production code, write RED fixtures demonstrating SMA seed, cloud population stdev, warmup, as-of selection and numeric snapshot output. The expected EMA5 for closes1..10 is8; cloud size for closes1..100 is sqrt(833.25)/4.
- [ ] Vendor exact function bodies `_seeded_recursive`, `ema`, `stdev` from indicators.py and `emas`, `ema_cloud` plus TR_EMAS from tr.py. Only audited numpy/pandas and relative pure subset imports. Preserve attribution and describe behavior as pinned chart-desk, not an independent claim about TradingView. Record original blob hashes, commit, selected symbols and mapped consumer lines.
- [ ] Adapter consumes Task1 selector. On blocked history export all observations null: STALE for stale window, UNAVAILABLE otherwise. For usable history, emit per-period EMA price, close-above boolean, and signed EMA change over five bars with 2*n warmup; UNKNOWN during warmup. The unnormalized delta is source T3 numerator, not an ATR-normalized slope or momentum score.
- [ ] Emit available EMA descending order as a categorical period list (stable tie order as source), full-fan stacked boolean only after all EMAs meet warmup, cloud50 basis/upper/lower/size and close location ABOVE/BELOW/INSIDE after100bars. Partial order remains usable when only some averages exist. Record partial/full coverage separately; no invented equality direction.
- [ ] Use namespaced feature IDs `chartdesk.<timeframe>.ema<n>`, `.above_ema<n>`, `.ema<n>_delta5`, `.ema_order`, `.ema_stacked`, `.cloud50_<basis|upper|lower|size|location>`. All raw numbers unrounded; no outcome features. Known timestamps last closed bar and max availability of ALL selected dependencies. Missing/warmup timestamps record evaluation atT. Use existing build_snapshot; all feature definitions PRE_ENTRY/required=False.
- [ ] Add canonical selected-input SHA256 and metadata including exact instrument, timeframe, history_start, freshness, source commit, adapter version and pandas/numpy versions. Excluded future rows cannot change payload/identity at the same T. Reports always ready_for_replay=false/ready_for_training=false.
- [ ] Add standalone read-only parity CLI taking explicit --source-root (chart-desk checkout). Compare selected function ASTs and source Git blob identities against pinned manifest, before executing ONLY the reviewed vendored functions. No dynamic exec or import from source checkout. Functional golden tests establish numerical behavior; source AST identity demonstrates reuse. Mutated source must fail (nonzero exit), no skip if source missing.
- [ ] Tests: 5/15/30/60/240m aligned closed inputs, short/full warmup, known False/zero retained, equality in cloud, rising/falling/mixed/tied order, stale/gap/allmissing, late earlier dependency availability propagated, future suffix extreme changes excluded, caller input/output nonmutation and deterministic identity, all-finite output. Reject numerical overflow rather than turn it into warmup.

