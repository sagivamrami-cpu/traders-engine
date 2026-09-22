# Complete original extension-state calculation over offline inputs

Architectural dependency within approved master C/D: reconstruct actual
still_valid inputs, not a replacement strategy or a new signal. Existing source
behavior remains authority; no new domain threshold, feed alias or approval.

## Authority and alternatives

chart-desk commit68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9.
stretch.py blob a74a591d9f3e014543e4023c694eab7eac845d43;
rails.py blob614920678bc58f1b920ebd145b1a4b0b5a159dff.
Read both actual BUDGET_MIN and full stretch.py, not only the comments.

A supplied is_extended boolean would conceal calculations and source reads.
A fresh implementation from the prose would change the source's actual rails.
Chosen: complete source calculation/rendering over two offline source ports,
calling the existing real EMA/range implementations. No retained source code
is imported or executed. Source AST extraction is inert.

## Runtime projection

Create private _vendor/stretch.py. Imports: future annotations, dataclass,
`from . import tr, ranges`. Copy BUDGET_MIN assignment from rails.py before
all selected stretch globals. Preserve BEYOND_MIN, BEYOND_EXTREME, DEV_STRETCHED,
complete Stretch dataclass with properties/contradicts/line/render, and _atr.
Place StretchReader after these symbols, constructor(source) stores self.source.
Original _dev_from_cloud and state become methods, in source relative order.

Only changes to these function bodies:

- _dev_from_cloud: basis.fetch_corrected(symbol,tf,days) ->
  self.source.fetch_corrected(symbol,tf,days).
- state: basis.fetch_corrected(symbol,"1d",400) -> source equivalent;
  basis.broker_shape_ok(dcorr,20) -> self.source.broker_shape_ok(dcorr,20).
- state: tr.tr_levels -> ranges.tr_levels; tr.weekly_from_daily ->
  ranges.weekly_from_daily (exact call-expression replacements).
- state: _dev_from_cloud(symbol,tf,days) -> self._dev_from_cloud(symbol,tf,days).

Signatures preserve original arguments/annotations/returns with self prepended.
All try boundaries, short circuits, loops, numeric behavior, original docstrings
and rendering stay intact. _atr keeps its local pandas import, unseeded ewm.
No symbol normalization, frame trimming, new correction veto or finite filter.

Ports: fetch_corrected(symbol,timeframe,days)->(df,correction), and
broker_shape_ok(correction,days)->bool. Ports are explicit local inputs. Actual
causal feed binding/clock/evidence remains separate; the raw runtime cannot
certify arbitrary frame provenance. Tests use real broker_shape_ok_at and an
explicit clock, not a fake stretch boolean. No network/filesystem IO by runtime.

## Behavior and discrepancy against source prose

Daily400 is followed by broker_shape_ok20 only for nonempty daily. Failed
fetch/shape/range calculation returnsNone. Range result must be available and
verified with nonzero ADR and nonmissing rails. No deviation reads before that.
Complete tr_levels(daily,weekly_from_daily(daily),broker_bars=True) executes.

Actual default ADR is14 prior daily rows; current row excluded. Rails from
average_range(from_open=True) are open +/- ADR/2. Source Stretch comments say
open +/- ADR and ADR20; these are NOT the executable formula. Keep raw source
docstrings for audit, prominently explain the discrepancy in public usage.
The shape horizon20 is not an instruction to average20 days.

Budget=(today.high-today.low)/ADR. beyond=(close-nearest crossed rail)/ADR,
side up/down orNone. is_extended requires budget>=1.25 AND beyond>0;
direction/contradicts reflect the same side, not an opposite reversal forecast.
Always attempt deviations in order15m20,1h60,4h240 after usable daily even when
not extended. Each requires>=60 bars, real tr.emas EMA50 and independent _atr.
Missing/failed/zeroATR drops only that deviation. Corrections are ignored on
these deviation reads by original code. NaN behavior is not silently repaired.
Thresholds0.50/3.0 affect rendering tier and cloud-distance line only.

## Verification

Use real synthetic daily/intraday frames, actual ranges/EMA and correction
shape predicate. Hand literals: prior ranges20, current O100/H126/L100/C116
gives rails110/90,budget1.3,beyond0.3,long; mirror C84/H100/L74 gives short.
Prepend different old ranges to catch wrong14-vs20 average. Exclude current
range from ADR. Linear60 closes100..159 with H=C+1/L=C-1 give EMA50=134.5,
ATR2, deviation12.25. Two true ranges2 then20 give unseeded ATR23/7.
Cover both boundaries, no-extension rendering, cloud tiers, shape failure,
missing/short/zero data, narrow per-timeframe failures, no input mutation,
splice20day clock boundary, nativeBTC correction and unchanged symbol requests.

Independent auditor pins HEAD/root/baseline and both source blobs. Compare
complete ordered runtime AST including imports/classes/signatures and exact
substitution cardinalities. Invoke existing range audit and strict ordered EMA
audit (literal dependency blobs); do not rely on old unsealed EMA manifest.
Runtime/source/dependency mutations must block. CLI explicit parent source root,
JSON VERIFIED0/BLOCKED2; replay/training readiness alwaysFalse. Audit never
imports candidate/runtime/source. Task and final review precede acceptance.

Still required afterwards: real historical provider binding, complete EMA-deep/
calendar/tree revalidation, full lifecycle/effects/caller and all other master
branches, economic simulator, dataset, models and empirical evaluation.
