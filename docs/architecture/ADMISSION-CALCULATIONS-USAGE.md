# Original admission calculation dependencies

Status: accepted after independent task/combined and scoped fix reviews; see
agent-exchange/status/2026-09-09T125556Z-codex-admission-dependencies.md. This is a private pure
calculation subset, not the outer producer gate or a replay-ready public adapter.

Pinned sources: chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9 and
trading-floor d827dd792cbd1d396b4ee325879c63e57388e07a.

## Interfaces

Under `trading_system.tree_replay._vendor`:

- `admission_matrix.read_frame(df, tf, basis_note=None)` computes the original
  TFView, retaining close, TR/SuperTrend/VWAP/structure readings, ATR, bar timestamp,
  weighted net agreement, label and agree counts. No feed fetch or correction
  rendering happens. Caller supplies a validated causal frame; this private
  function does not enforce publication cutoffs or validate a timeframe label.
- `admission_toolkit` contains original SuperTrend ladder and UTC-day VWAP bands.
  `admission_indicators` preserves its seeded ATR, separately from the matrix's
  unseeded TR ATR. Existing audited EMA dependencies remain unchanged.
- `admission_quality.evaluate` and its original parsers annotate named anchors,
  triggers and supplied rejections. `shadow_block` is a descriptive hypothetical
  policy, not a real veto. This function does not select fresh rejection history.
- `admission_clocks.outside_reason(now)` and `entry_blocked(now)` require aware
  decision time. Missing/naive time is rejected; no fallback to wall clock.
  The former uses02:00 inclusive to21:00 exclusive Jerusalem hunting hours;
  the latter the source weekend/preclose policy. Apply caller ordering when
  eventually binding them. Neither is a historical market-data session calendar.
- `admission_swing._last_swing(df, up)` preserves SWING_K3 and exact comparisons.
  A center needs three bars on its right; its timestamp is not availability.

## Source behavior that must remain visible

Matrix strengths are descriptive, not success probabilities. Source weights:
TR1.0, SuperTrend0.8, structure0.8, VWAP0.6. The net divides the weighted signed
strength sum by the sum of included weights. The source post-stop caller and
lifecycle higher-bias caller use different decision conditions; this module
does not replace either caller with one generic gate.

The source VWAP uses equal weights if total volume is zero/missing, groups by
UTC date, and may yield NaN z on a zero-variance day. In `read_vwap`, source NaN
comparisons then yield direction-1 and strength100 rather than an unavailable
reading. A synthetic60-flat-bar frame produces net-41.25 across the full matrix.
The one-bar warmup also retains source-specific NaN behavior. These are measured
code behaviors, not sensible probability estimates or validated trading edge.
They are intentionally not silently repaired in a pinned-baseline port. The
future public frame/feature binding must expose data-quality/anomaly provenance;
changing the source decision itself is a separately named variant.

## Audit and verification

`configs/trees/admission-source-contracts.json` records source blobs, ordered
definitions, dependency modules/imports and allowed specializations. The auditor
has an independent fixed closure, so editing the manifest cannot narrow checks.
It reads source as inert text, checks repository roots/HEADs/blob hashes, and
compares full ordered vendor ASTs including shared EMA/TR dependencies. It never
imports or executes the retained live desks. Runtime calculations work without
the retained checkout; the audit requires it explicitly.

```powershell
python -m pytest tests/tree_replay/test_admission_calculations.py tests/tree_spec/test_admission_source.py -q --tb=short
python tools/check_admission_source_parity.py --source-root 'C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149'
```

Local recovery verification:93tests passed; source_subset_verifiedtrue, empty
blockers, readinessfalse. Worker RED evidence/report was not recovered, so no
claim is made about its completed TDD process. See latest exchange status for
review/acceptance rather than inferring acceptance from test counts.

Still required: causal frame binding, full rejection-log prefix/tail selection,
actual tracker/episode gates and recording, source lifecycle transitions,
other producers/arbitration, simulator, real data, labels and trained models.
