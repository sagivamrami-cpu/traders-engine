# Original EMA windows and optional deep prehistory

Private module: trading_system.tree_replay._vendor.ema_windows.
Source authority and exact adaptations: EMA-DEEP-READER-CONTRACT.md.
Runtime, tests and source auditor accepted after independent task/final reviews;
see agent-exchange/status/2026-09-09T211034Z-codex-ema-deep-reader.md.
This is not the existing public ema_snapshot and does not change that adapter.

EmaReader(source).read(symbol,timeframe,lookback=None) runs real original EMA
state calculation. read_stack(symbol,timeframes=('4h','1h','15m','5m')) reads
each in order and omits only reads that raise, preserving repeated requests.

The supplied local source has exactly these methods:

```python
fetch_corrected(symbol, timeframe, lookback)  # -> (DataFrame, correction or None)
deep_exists(logical_path)                    # -> bool
deep_bytes(logical_path)                     # -> bytes
```

No default source is supplied. These must be offline evidence readers, not live
API or file fetches. Logical paths identify captured inputs, not paths this
runtime opens. Original symbol mapping and timeframe suffix yield names such
as deep/XAUUSD_H1.csv. A bare XAUUSD is not normalized for this lookup and skips
the leading-underscore filename. A known symbol with5m/unknown timeframe still
probes deep/XAUUSD_.csv, matching source. Do not infer a valid feed from a name.

Default request lookback is2200 for daily,2000 otherwise; source truthiness
means0 uses the default. Delivered history is not trimmed. Correction flags do
not veto this reader; corr.source is an annotation only. Frame fetch failures
propagate from read. Optional deep exists/bytes/CSV/time parsing failures are
caught and leave deepNone. DataFrame calculations after that try may still raise.

Deep CSV is parsed by pandas from supplied bytes, time converted to UTC and
rows sorted. For each of5/7/13/50/200/800, only insufficient live history (<2*n)
allows strict pre-live deep rows to seed the EMA. Overlap/newer deep rows cannot
replace the live endpoint. Duplicate removal and sorting of the combined frame
occur only on that splice branch, not as global normalization of all live data.

EmaState exposes actual windows, unconverged lengths, source, trends, stack,
glued5vs7, cascade, open-window magnet and weighted continuous slope summaries.
Window ATR and current close come from the supplied live frame. Slope spans3
EMA bars and uses ATR of the final20 source rows for histories longer than20;
that span can include deep rows if the live segment is short. It is not the
old adapter's5bar delta or a necessarily live-only slope denominator.

Source numerical behavior is retained. No floating epsilon is inserted into
trend comparisons: even constant100 can give EMA200100.0000000000001 and a
negative tiny distance. Exact-flat tests use128 to isolate true zero/None
semantics from rounding. Zero ATR can leave slope unknown; neither NaN nor
unconverged windows are certified numerical model features by this raw reader.

All history availability, current-bar policy, period calendars, ordering,
warmup, price basis, deep splice identity and observed/available times are
caller obligations until real causal binding is implemented. GC prehistory is
not automatically approved as spot history, and deep bars must not feed ADR or
range calculations. Rendering returns text only; there are no sends or trades.

Run tests/tree_replay/test_ema_windows.py for current synthetic behavior and
tests/tree_spec/test_ema_windows_source.py for inert source/dependency drift checks.
The explicit source audit is:

```text
python -B tools/check_ema_windows_source_parity.py --source-root <retained-parent>
```

It requires the pinned chart-desk checkout under that parent and returns JSON,
exit0 for VERIFIED or exit2 for BLOCKED, never replay/training readiness. It
parses the entire projected module and the real ordered seeded-EMA dependency;
it does not import the reader or execute retained source. Independent component
acceptance is recorded in the status above; see2026-09-09-ema-deep-reader.md. Full
revalidation/caller/lifecycle/economic dataset/model work remains beyond it.
