# Offline level-reversal setup adapter

This is the detection half of one existing producer, not the full tree, a trade
simulator, or a trained model. The live alert implementation is unchanged.

## What it does

The pinned chart-desk `level_reversal.detect_frame` searches closed M5 or M15
candles for a reversal at a supplied eligible level. M5 requires a red/green
climax vector and a following confirmation; M15 also allows violet/blue rising
volume vectors in a single completed candle. Direction of arrival, level crossing,
midpoint conditions, contiguous pattern candles and level eligibility are copied
from source, not newly chosen research thresholds.

The source commit is `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`.
The vendored PVSRA function specializes ONLY the default non-auction branch.
Auction/seasonal modes are neither enabled nor silently approximated.

## Inputs

Use `ClosedBar` inputs from `trading_system.tree_replay.bars`, with exact
venue:symbol identity and closed/available timestamps. The existing contiguous
selector is the default. An explicit `SessionSchedule` opts into the already
documented complete-session-history policy; the detector still refuses patterns
whose own two or three candles straddle a scheduled break.

Supply `NamedLevel(name=..., price=...)` and an immutable `LevelSnapshot`:

```python
from trading_system.tree_replay.levels import NamedLevel, LevelSnapshot
from trading_system.tree_replay.reversal import detect_reversals_asof

# closed_bars, observed_at, published_at and decision_time come from the
# caller's independently retained historical evidence, not datetime.now().
level_state = LevelSnapshot(
    snapshot_id="level-state-reference", instrument="CME:GC",
    version="supplied-calculator-version", source="supplied-evidence-reference",
    observed_at=observed_at, available_at=published_at,
    levels=(NamedLevel(name="PSY-LO", price=level_price),),
)
result = detect_reversals_asof(
    closed_bars, snapshot_id="evaluation-reference", instrument="CME:GC",
    timeframe="5m", decision_time=decision_time, history_start=history_start,
    max_age_seconds=bar_age_budget, level_snapshot=level_state,
    max_level_age_seconds=level_age_budget,
    # session_schedule=explicit_schedule,  # optional
)
```

This fragment illustrates the interface, not a source of real levels or a choice
of age budgets. Instrument examples do not establish futures/CFD equivalence.
All budgets are explicit positive integers; metadata is required and times must
be timezone-aware and microsecond-exact. Level prices must be finite positive
native numbers. Repeated names require distinct explicit `level_id` values and
different prices; duplicate IDs or name/price pairs are rejected. Tuple order
is preserved for ties. IDs are optional when display names are unique.

A level snapshot must be observed no later than the latest selected confirmation
close and available by the decision time. A late publication can be evaluated
later, with that later availability recorded. A post-confirmation revision is
not silently used to reconstruct that confirmation. The adapter evaluates ONLY
the latest selected confirmation; a historical loop must supply the appropriate
level snapshot for each decision. It does not persist or deduplicate such a loop.

## Output states

| Status | Meaning | Not equivalent to |
| --- | --- | --- |
| BLOCKED | Input evidence is missing, stale, insufficient or unavailable | Tree rejection or losing trade |
| NO_CANDIDATE | Usable supplied inputs produced no current setup | Losing trade |
| DETECTED_UNPRICED | Source pattern found, with its direction and level anchor | Approved trade, fill or profit |

`blocker` distinguishes window failures, `LEVELS_UNAVAILABLE`,
`LEVELS_AFTER_CONFIRMATION`, `LEVELS_STALE`, `WARMUP`, and `VOLUME_UNAVAILABLE`.
The first applicable blocker is returned, not an exhaustive diagnostic list.
Malformed inputs (including duplicate bars and instrument mismatches) raise
`ValueError`. Missing volume is not converted to zero. An all-zero-volume selected
history blocks; a zero prior-volume average leaves the source classification
unchanged but exports an undefined volume ratio as `UNKNOWN`/null, not infinity.
Numeric overflow fails closed. At least 12 selected bars are required, as in source.

Each detected candidate contains the source pattern, vector kind, level name and
price, sweep extreme, confirming close and event timestamps. Direction is available
as LONG/SHORT and the original Hebrew source direction. `tradeable` is always
false; `trade_plan` is null. The level price is an anchor, not a simulated fill.

The nested pre-entry snapshot contains source level/pattern/arrival and PVSRA
volume, prior-10 mean, volume ratio, spread-volume, prior-10 maximum, climax/rising
flags, sweep and confirmation close. This is only this detector's evidence, not
all 22 layers or a full feature registry. Missing other branches, Order Flow,
options, market structure, multi-timeframe context and admission gates are not
implicitly approved. NO_CANDIDATE currently carries diagnostics, not a full
negative-case feature trace; full-tree snapshot/trace integration remains pending.

Snapshot observation time is the confirmation close; availability is conservatively
the maximum of all selected bars, levels and optional calendar publication times.
The nested snapshot's `eligible` means only completeness of its declared optional
feature registry. It is NOT trade or training approval. Both top-level readiness
flags remain false for every output state.

## Identity and reproducibility

`source_event_id` preserves the original vector-open floor-to-15-minute bucket.
The source's within-call dedup instead uses the confirmation-close 15-minute
bucket. These are different concepts; neither was silently corrected. The source
chooses the nearest level to confirmation close, with original input order for
equal-distance ties.

`candidate_id` includes source commit, producer/timeframe, source event and exact
confirmation time. It identifies a setup event, not a complete evaluation or a
cross-producer execution. `evaluation_sha256` fingerprints the selected window,
level snapshot, optional schedule, budgets, decision time and calculation versions.
Re-evaluating the same setup may retain its candidate ID while its evaluation hash
changes. Use the evaluation hash when distinguishing revisions/measurement states.
Future bars are not selected; unavailable level values are not exported as features.
Hashes and metadata are diagnostics, never model feature columns.

Adapter v2 includes optional level IDs in serialized evidence; v1 evaluation
hashes must not be reused as v2 hashes. Numerical detection and candidate event
identity are unchanged. Distinct Q-QUARTER locations can now retain their source
display names without ambiguity.

The caller must retain actual bars, levels, schedule and dependency evidence in
an approved storage location; a digest alone cannot reconstruct inputs or prove
they really existed at the claimed time. No raw feed data was acquired for this
implementation, and no new data-retention permission is implied.

## Verification and next boundary

Run `python -m pytest tests/tree_replay/test_reversal.py -q` for synthetic wrapper
cases, and `python -m pytest tests/tree_replay/test_reversal_source.py -q` for the
pure subset and tamper checks. `tools/check_reversal_source_parity.py --source-root
<retained-chart-desk>` reads the pinned source for hash/AST verification without
importing or executing its live package. Subset parity is not whole-alert parity.

An additive pricing adapter is now described in REVERSAL-PRICING-USAGE.md;
the detection-only API remains unpriced. Next work: construct historically
reproducible level-map inputs, then admission, cross-producer arbitration and
execution/outcome simulation. Only afterwards can candidate histories become the
approved profitability/movement dataset. No historical win rate is established here.
