# Offline original level-map calculation graph

This low-level graph preserves the complete `chartdesk.levelmap.build` calculation
at chart-desk commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`. It consumes an
explicit offline source and decision time. It is not a frame validator, full
historical replay, producer admission, outcome simulator or training interface.

```python
from trading_system.tree_replay._vendor.levelmap_build import build_at

missing = []
levels, daily_correction = build_at(
    "OANDA:XAUUSD", missing,
    source=validated_offline_source,
    decision_time=validated_decision_time,
)
```

`validated_offline_source` is supplied by the caller; this module neither creates
one nor resolves a feed. Its two methods are:

```python
fetch_corrected(symbol, timeframe, lookback_days)  # -> (DataFrame, Correction | None)
broker_shape_ok(correction, days)                 # -> bool, evaluated at caller's T
```

Frames use the original OHLC columns and datetime index conventions. The caller
owns exact instrument/frame binding, correction evidence, chronology, completed
and forming bars, history completeness, publication cutoffs and clock validation.
The injected shape method can delegate to the accepted
`correction.broker_shape_ok_at(..., decision_time=T)` after validating evidence.
It must use the same decision time as the graph. Do not pass `None` as a clock;
the graph deliberately adds no new validation to the original calculation path.

The fetch sequence starts with `1d/400`, then `5m/3` for session opens, then
`1h/20` with conditional `15m/20` for PSY, and finally `1h/240` and `4h/240` for
EMAs. The lookbacks are original request arguments, not proof that a supplied
frame covers those windows. The first returned correction is the daily one.

The full original `NamedLevel` dataclass, including its representation, is
preserved. Output is an ordered list, not a name-keyed dictionary: distinct
prices can share `Q-QUARTER`. Stable identity belongs to the downstream adapter.
The source return annotation retains the quoted `basis.Correction` expression;
there is no global live `basis` import to resolve it through `get_type_hints`.

## Original behavior retained

Emission order is ADR, AWR/RW/AMR, ADR50/AWR50/AMR50, RD, yesterday, D2–D4,
last week, day/week opens, London/NY opens, PSY, selected EMAs and quarter grid.
Floor pivots remain internal range dependencies and are not emitted. No extra
session opens or EMA periods are added.

| Family | Original requirement or behavior |
| --- | --- |
| ADR / RD | Daily broker shape is assessed over 20 days; ADR additionally needs availability and verification, RD requires verified numeric rails |
| AWR / RW / AMR | Original availability/high guards; they do not inherit ADR's broker veto |
| From-open rails | Original available rails at period open ± half mean range; remain possible on proxy evidence |
| Prior days and opens | Source yday/back-day/weekly history guards; no added blanket correction veto |
| London / NY | Exact same-day venue opening bar, start inclusive/end exclusive, venue DST and weekdays; missing or `source="none"` correction omits opens |
| Spliced session opens | Opening timestamp must be at or after `tv_from`; equality is accepted |
| PSY | Shape over 7 days; first accepted nonempty 1h frame, otherwise 15m; splice clipped before calculating range |
| EMA200/800 1h | At least 400/1600 bars respectively and a non-null final source EMA |
| CLOUD50/EMA200 4h | At least 100/400 bars respectively; CLOUD50 is EMA50's basis, not a cloud edge |
| Quarters | Real existing `quarters.nearest(..., count=2)`; prices and stable nearest ordering preserved |

PSY uses Sydney Saturday 08:00 for crypto (symbol contains BTC), Sunday 08:00
for forex, through the following local day's hour strictly before 17. The
window logic, median resolution requirement of at most 1h, grouping gap strictly
greater than 12h, and planned `window_end` are copied exactly. The source's
comments describe its convention; they are not holiday/calendar certification.
The last available window may still be forming and still emit PSY levels.

An accepted 1h frame that becomes empty after splice clipping stops fallback.
Likewise, a coarse accepted frame or one with no PSY window does not trigger a
15m retry. A fetch exception in the PSY block exits that entire block. These
are retained source behaviors. Missing-family strings and exception boundaries
are preserved, including silent omissions; `missing` is not a complete coverage
or eligibility report. Daily fetch failure returns `([], None)`; malformed daily
frames can still raise after fetching because input validation belongs upstream.

Source identity is deliberately asymmetric: native BTC can pass shape checks
with `source="none"` while its session opens remain omitted. `source="replay"`
does not pass OANDA's daily/PSY shape gate but can supply session opens. No
correction is relabeled and no offsets are applied. The existing quarter
dependency's symbol matching is not authority to alias GC to OANDA.

## Projection and audit

`_vendor/levelmap_build.py` contains only the required imports, complete
`NamedLevel`, `SESSION_OPEN_LEVELS`, the two helpers and `build_at`. The only
function changes are required keyword-only source injection with local
`basis = source`, the prescribed helper/build names and keyword propagation,
and explicit `decision_time` replacing the session helper's optional clock.

`_vendor/map_sessions.py` preserves complete `SessionSpec`, `SESSIONS`, `_hm`
and `psy_levels` in source order. `_vendor/map_tr.py` only composes accepted
EMA and range functions. Existing quarters/back-days/correction dependencies
are reused without changes.

```powershell
python -m pytest tests/tree_replay/test_levelmap_source.py -q --tb=short
python tools/check_levelmap_source_parity.py
python tools/check_levelmap_source_parity.py --source-root C:/path/to/pinned/chart-desk
```

Root precedence is explicit `--source-root`, then `TR_CHARTDESK_SOURCE_ROOT`,
then the retained review checkout recorded in the tool. Missing source is a
failed prerequisite, never a skipped test. The audit parses text only; neither
the source checkout nor the vendored calculation modules execute during audit.

The tool independently pins commit, source blobs, complete manifest, imports,
symbol order, composition and AST transformation preconditions. Whole-module
AST comparison rejects extra statements, imports, rebinding and missing code.
Baseline configuration must contain exactly one matching chart-desk commit.
JSON false is distinguished from numeric zero.

Every audit invokes the range, pricing (including reversal), EMA and correction
audits. Their accepted manifests are independently sealed by canonical JSON
SHA256 (`json.dumps(sort_keys=True, allow_nan=False)` in UTF-8), including the
inherited reversal manifest. Legitimate dependency contract changes require a
separately reviewed pin update.

The new graph auditor also independently checks complete ordered projections of
the accepted EMA vendor modules. `chartdesk/indicators.py` is pinned to blob
`672f0428c3a81b86376d4f792ae40ecd174a2025` and `chartdesk/tr.py` to
`8297c712d20404880d4d8949e96efbf48613909c`, verified from the pinned commit's
Git objects before adding these checks. Imports, constants and functions must
match source order; only an optional initial vendor module docstring is ignored.
In particular, `TR_EMAS` must precede `emas`, whose default argument uses it.
Noninitial strings, duplicate imports and reordered declarations are rejected.

This closes two demonstrated inherited-EMA gaps without editing the old tools:
a coordinated indicators source/vendor/manifest change cannot establish a new
trusted source pin, and set-equivalent vendor reorderings cannot pass the full
graph audit. Tests first show the unchanged old audit accepting those mutations,
then assert that the new graph audit blocks them. All mutations occur in
relocated copies; neither the source nor the vendor is executed in those audits.

Exit 0 means the specified source subset and dependencies verified. Missing or
changed inputs return a blocked JSON report and exit 2. Expected dependency
read/parse/import failures are reported, and one failed audit does not skip the
other dependencies. `ready_for_replay` and `ready_for_training` always remain
false, including successful audit reports.

The causal frame builder and public historical-map adapter are independent
downstream work. This Task 1 graph does not certify historical holidays, live
bar parity, data provenance, admission/arbitration, fills, economics or readiness
for the full tree-outcome model plan.
