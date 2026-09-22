# Historical EMA observation adapter

This is an offline calculation slice of the approved tree-learning plan. It
does not create trade candidates, simulate fills, label market trades or train
a model. The existing live alert system is unchanged.

Implementation plan: `docs/superpowers/plans/2026-09-09-asof-ema-adapter.md`.
Source/consumer mapping: `configs/trees/ema-feature-contracts.json`.

## What is reused

Pure function bodies from chart-desk commit
`68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9` are preserved in
`trading_system/tree_replay/_vendor/`. Only numpy/pandas and the local pure
subset are imported. The live desk package is not imported or executed.

- EMA5/13/50/200/800 use the original full-window SMA seed and recursion.
- EMA50 cloud uses population stdev of the last100 closes divided by4.
- Observation availability follows `features.draw_trend`: each EMA requires
  twice its period in history, not merely a computable seed.
- Exported `ema<n>_delta5` is the signed five-bar difference, the numerator of
  source T3. It is NOT the original ATR-normalized slope. ATR, fan width,
  compression, vectors, levels and the remaining drawer fields are not covered.
- Price-above, descending EMA order, full-fan stacked status and cloud location
  preserve source comparisons. Equal cloud boundaries count as INSIDE; equality
  with an EMA is not above. Tied EMAs retain stable period order.

No rounding is introduced. The source's floating-point effects remain: a constant
price100 can give EMA200=100.0000000000001 and therefore a different sorted order.
An exact power-of-two constant128 provides a genuinely tied synthetic fixture.
Neither stacked status nor any other observation is an entry rule here.

## Input boundary

Supply `ClosedBar` objects from `trading_system.tree_replay.bars` with all required
fields: exact venue:symbol, timeframe, opening/closing/availability timestamps,
OHLC, volume (explicit None permitted), and source identity. Values must be finite
native int/float; OHLC positive with valid geometry. None volume is not zero.

Supported fixed durations are5m,15m,30m,1h,4h. Timestamps are normalized to native
UTC datetime. Aligned datetime subclasses are accepted; sub-microsecond timestamps
are explicitly unsupported, never rounded. Nanosecond feed ingestion needs a
separate exact-time contract before using this adapter with such data.

Every call requires a decision time, history anchor and positive integer freshness
budget in seconds. Only bars opening at/after the anchor, closing at/before the
decision, and available at/before it may enter the calculation. The latest usable
bar need not be the most recent chronological bar if publication was delayed;
the caller's explicit freshness budget decides whether the older window is stale.

Input order is normalized; duplicate opens/revisions and mixed identities are
rejected. Missing anchored first bars, interior gaps and stale endings are
reported explicitly. Even invalid excluded records are rejected, not silently
interpreted as a revision policy.

This first boundary accepts contiguous segments only: it does not know weekends,
holidays, session breaks or broker bar alignment. Do not use it to claim a
multi-year market replay; calendar-aware history and the existing feed policies
must be reconciled next. Partial higher-timeframe bars are not supported either.

## Synthetic example

```python
from datetime import datetime, timedelta, timezone
from trading_system.tree_replay.bars import ClosedBar
from trading_system.tree_replay.ema import ema_snapshot

start = datetime(2026, 9, 9, tzinfo=timezone.utc)
bars = [ClosedBar(
    instrument="SYNTH:TEST", timeframe="5m",
    opened_at=start + timedelta(minutes=5*i),
    closed_at=start + timedelta(minutes=5*(i+1)),
    available_at=start + timedelta(minutes=5*(i+1)),
    open=i+1, high=i+2, low=i+1, close=i+1,
    volume=None, source="synthetic demonstration",
) for i in range(10)]
result = ema_snapshot(
    bars, snapshot_id="demo", instrument="SYNTH:TEST", timeframe="5m",
    decision_time=bars[-1].closed_at, history_start=start,
    max_age_seconds=300,  # synthetic choice, NOT an approved market policy
)
assert abs(result["features"]["chartdesk.5m.ema5"] - 8) < 1e-12
assert result["availability"]["chartdesk.5m.ema13"] == "UNKNOWN"
assert result["ready_for_replay"] is False
```

Each frame produces22 typed observations. Call separately for each supported
frame at the SAME explicit decision time; no multi-frame join or producer
arbitration is implemented yet. Prefixes such as `chartdesk.5m.` prevent an
accidental join of different timeframes or legacy layer IDs.

## Output and provenance

The payload extends the existing pre-entry snapshot with exact instrument/frame,
history anchor, freshness limit, selected-bar count, per-EMA history coverage,
window blocker, source commit, adapter version and installed pandas/numpy versions.
`window_sha256` identifies selected bars and their metadata plus window settings.
Valid excluded future rows do not affect the payload at a fixed decision time.

Known observations carry the last selected bar's close time and the maximum
availability of ALL selected dependencies, including late earlier bars. Missing
and warmup observations record the evaluation time and explicit status. Unknown,
unavailable and stale values remain null; legitimate false and zero remain values.

All fields are optional PRE_ENTRY observations. The inherited snapshot `eligible`
flag is only required-field completeness and can be true even when this optional
observation set is missing. Never treat it as candidate, replay or training
readiness. Both `ready_for_replay` and `ready_for_training` remain false.

The caller owns persistence; this adapter does not yet append an immutable dataset.
The input hash is not a substitute for pinning the eventual research-code revision,
dependency environment and contract manifest in a dataset/experiment manifest.
Repeated full-window computation is for fidelity testing, not a claimed optimized
ten-year engine. Checkpoint/resume equivalence remains separate work.

## Verify source reuse

```powershell
python tools/check_ema_source_parity.py --source-root C:/research/chart-desk
```

The directory is an example path; the command does not download it. It compares
canonical LF Git blob identities for indicators/tr/features and the selected
function/constant ASTs against the local audited subset, including its allowed
imports/top-level nodes. Nothing from the input directory is executed.

Required file/symbol/import coverage is checked before source access: an empty,
partial or duplicated mapping cannot verify. The trusted manifest's blob hashes
are not independently authenticated against Git history by this command; use the
separate baseline checker for checkout HEAD/worktree identity. This tool neither
protects against edits to itself nor certifies the consumer's full semantics.

Exit0 means source subset identity verified, exit2 means missing/mismatched
source or subset, exit1 means invalid local contract/input configuration. This
is source reuse evidence, not deployed-service or full-tree replay parity.

## Next integration boundary

An opt-in session-aware extension now has its own
`docs/architecture/SESSION-EMA-ADAPTER-USAGE.md`. The contiguous behavior described
above remains the default. The extension does not certify historical overlays.

Reconcile the existing `trading_system/data_foundation/sessions.py`,
`configs/data/gc-session-calendar-construction-policy.yaml` and
`configs/data/gc-missing-bar-policy.yaml` before adding session-aware continuity.
The stored calendar describes research normal hours, not universal historical
execution truth. Its era/overlay qualifications must remain visible. The legacy
missing-bar contract's15-bar feature lookback is not the new EMA800 dependency
window and must not be silently reused for these observations. This note identifies
existing integration points; it does not approve new dataset construction.
