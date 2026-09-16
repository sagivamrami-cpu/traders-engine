# Offline original tracker admission and recording

This private dependency executes the pinned original exposure, post-stop,
same-level and record decisions on explicit supplied ports. It does not bind
the market-watch loop, generate subsequent tracker lifecycle transitions,
simulate economic fills/exits, produce labels or authorize training. Acceptance
belongs to the controller's exchange status, not this usage document.

Source authority: chart-desk `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9` and
trading-floor `d827dd792cbd1d396b4ee325879c63e57388e07a`. The latter remains a
required baseline identity; none of its live code is imported by this closure.
All runtime code is static under `trading_system/tree_replay/_vendor/`.
Retained checkouts are read only as inert text by the auditor.

## Calling the private closure

```python
from trading_system.tree_replay._vendor.tracker_admission import TrackerAdmission

tracker = TrackerAdmission(source)  # explicit per-instance offline ports
occupied = tracker.has_open(symbol, direction)
stop_reason = tracker.blocked_after_stop(symbol, direction, plan)
level_reason = tracker.blocked_same_level(symbol, direction, plan.entry)
# Caller controls source gate order and whether recording is appropriate.
recorded = tracker.record(plan, variant="engine", to_group=False)
```

This example is not the full outer admission sequence. `record` accepts the
private source `pricing.Plan` geometry; it does not itself certify producer
admission or run all three gates shown above. `to_group` only stores the source
advisory flag; it has no messaging or broker side effect.

The source object must implement all these ports, with no host discovery or
wall-clock defaults:

| Port | Required supplied behavior |
| --- | --- |
| `now_epoch()` | Explicit decision epoch, float |
| `load()` | Detached dict of source advisory rows; unavailable state raises |
| `save(rows)` | Offline transactional sink; failure raises |
| `locked()` | Context manager spanning source load, recheck, mutation and save |
| `read_symbol(symbol, tfs)` | Original TFView-compatible values with `net` and `bar_ts` |
| `fetch_corrected(symbol, timeframe, lookback_days)` | Supplied `(DataFrame, correction)`; source post-stop call is `15m`, 5 days |
| `event_log_reader()` | Fresh seekable binary context manager over the entire causal log prefix; unavailable/open/read failure raises |
| `quote_payload()` | Source mapping from symbol to `lp`/`ts` rows |

The reader factory is passed without calling it to `_tail_reader(open_reader,
window=400000, cap=8000000)`. Opening occurs inside the original try/with;
opening, seeking, reading and context-manager failures return `None`. The source
algorithm seeks to the end, reads the tail, drops a leading partial line, and
expands the window by four when needed. A pathological last line may trigger the
original full-prefix fallback; the cap is not an absolute bytes-read limit.
The ordinary 10 GB virtual-prefix test reads exactly 400,000 bytes.

`_tail_bytes(raw, window=400000, cap=8000000)` is only a small-fixture convenience
using a lazy `BytesIO` factory. It returns `None` for `raw=None`; empty bytes are
an empty log. Runtime rejection selection never eagerly asks for a full byte
prefix. No reader implementation backed by files/services is supplied here.

All source method signatures retain their original arguments after `self`:
`has_open`, `blocked_after_stop`, `blocked_same_level`, `record`, `_record_locked`,
`_born_in_zone`, `_entry_band`, `_higher_bias`, `_thesis_baseline`, `_live_prices`,
`_recent_rejection`, `_cooldown_release`, and `thesis_now`. `_trade_identity`,
`_anchor_names` and `thesis_verdict` are module functions. The exact pure
`tradeplan.born_in_zone` helper is also included in this private module because
the accepted pricing subset does not contain it; no accepted runtime file was
extended. Its `entry_zone` dependency comes from the audited private pricing.

## Source behavior retained

- Only OPEN occupies a symbol/side. PENDING does not. Missing/corrupt exposure
  state fails closed, while the source post-stop and same-level outer catches
  return no block. Unknown explicit state names follow the original comparisons.
- Latest same-symbol/side STOPPED controls post-stop. At four hours it releases
  before matrix/frame reads. Earlier it sums 4h/1h at the original +/-25 boundary,
  then tests the confirmed source swing on at least eight strictly post-stop
  rows, then tests entry beyond the old stop by source symbol pip. The long/short
  swing asymmetry is preserved. Anchor changes/rejection are optional telemetry.
- Same-level checks DONE/CANCELLED, nonzero resolved time, age below 7200 seconds,
  and inclusive entry-band edges. First matching row wins. Future rows can match;
  causal state filtering remains the future binding's responsibility. Malformed
  fields can abort the source scan. Post-stop's eager `t['ts']` default is retained.
- Record reads higher bias, thesis and build/quote state before entering the lock,
  then reloads and rechecks OPEN. Complete geometry deduplicates PENDING/OPEN;
  resolved duplicates archive with the original integer send-time suffix. Suffix
  collisions retain original overwrite behavior. Failed saves propagate.
- Geometry identity canonicalizes source aliases, rounds eight decimals, hashes
  all target prices/style/stop to 16 hex characters, and rounds display entry to
  two decimals. Target names are not identity; order of prices is. This private
  source behavior does not authorize GC/OANDA feed substitution.
- Born-open requires a truthy build close in the entry band. Fresh quotes use a
  one-sided reached test. Missing/stale quote defers to build. Freshness is
  inclusive 0..420 seconds with finite positive price; future quotes are rejected.
  OPEN-at-send explicitly stores broker revalidation false and is not a fill.
- Higher bias requires both 4h/1h readings. Thesis uses the lower 30m/15m/5m
  average, breaking at signed -25 and recovering at zero. Deadband/unread baseline
  defaults to held. These are advisory readings, not economic labels.
- Rejection selection preserves original substring prefilter, UTF-8 ignore,
  malformed-JSON handling, inclusive stop/asof/max-age boundaries, overlap/gap
  and output rounding. Equal timestamps retain the first encountered row.
  Malformed numeric timestamps can raise outside JSON parsing; missing zone
  fields retain source permissiveness. Non-rejection log bytes affect the tail.

Every unavailable/error dependency must eventually be recorded by causal ports.
A swallowed source failure is not verified replay readiness. The independent
audit always reports `ready_for_replay=false` and `ready_for_training=false`.

## Verification

The auditor checks both repository roots/commits, baseline pins, canonical Git
source blobs, a fixed independent manifest authority, full ordered runtime ASTs
including imports/constants/methods and exact substitution preconditions. It
independently covers inherited pricing (all Plan fields and four original
properties), basis aliases, quarters, entry-quality and swing modules. It does
not infer this closure from a passing unrelated audit or execute retained code.

```powershell
python -m pytest tests/tree_replay/test_tracker_admission.py tests/tree_spec/test_tracker_admission_source.py -q --tb=short
python tools/check_tracker_admission_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
```

The runtime and source-audit tests use distinct basenames and run together under
the repository's default pytest settings. The combined dependency check is:

```powershell
python -m pytest tests/tree_replay/test_tracker_admission.py tests/tree_spec/test_tracker_admission_source.py tests/tree_replay/test_admission_calculations.py tests/tree_spec/test_admission_source.py tests/tree_replay/test_pricing_source.py tests/tree_replay/test_pricing.py tests/tree_replay/test_state.py -q --tb=short
```

Tests accept `TR_TREE_SOURCE_ROOT` as an explicit alternate retained parent.
Missing pinned checkouts fail descriptively; source evidence is never skipped.

Remaining full binding must reconstruct actual source log appends/spacing and
sessions, including pre/post detection and recording events. It must also bind
causal frames, publication mode, outer gate/producer ordering, active-before-
episode state, source lifecycle generation and separate economic simulation.

Component accepted in
`agent-exchange/status/2026-09-09T132950Z-codex-tracker-admission-source.md`.
Task/final reviews clean; fresh129scoped tests and source audit passed. Earlier
428integration tests overlap this scope; no whole-loop readiness is implied.
