# Original daily extension-state calculation

Private runtime: `trading_system.tree_replay._vendor.stretch.StretchReader`.
Source identity and complete permitted adaptations: STRETCH-SOURCE-CONTRACT.md.
This is the original calculated context used by later revalidation, not a new
signal, public historical provider, economic outcome or model feature export.

```python
from trading_system.tree_replay._vendor.stretch import StretchReader

# supplied_ports implements fetch_corrected(symbol, timeframe, days) and
# broker_shape_ok(correction, days); both operate on supplied offline evidence.
state = StretchReader(supplied_ports).state('OANDA:XAUUSD')
if state is not None:
    text = state.render()   # returns text only; sends nothing
    continued_in_stretched_direction = state.contradicts('לונג')
```

The complete calculation uses real existing range and EMA implementations.
Daily request1d/400 is checked by the supplied broker-shape predicate with20
days. When usable, source builds tr_levels with the real weekly conversion;
then attempts each deviation15m/20,1h/60,4h/240 in that order. Each uses>=60
rows, seeded EMA50 and its own unseeded ATR14. Requested days identify the
request; the runtime does not truncate the delivered history to that count.

## Important executable-versus-prose discrepancy

Source stretch comments describe rails as open +/- ADR and mention ADR20.
The actual called tr_levels defaults to ADR14; average_range(from_open=True)
returns open +/- ADR/2. These are the formulas preserved here. Twenty days in
the shape gate is a different quantity from14 prior rows in the average.

With prior14 daily ranges20 and current O100/H126/L100/C116, actual output is
ADR20, rails110/90, budget1.3 and beyond0.3. It is extended upwards and conflicts
with another long continuation, not automatically a short entry. Earlier old
rows with different ranges and today's range do not change the prior14 average.
This discrepancy is source characterization, not a silent strategy correction.

is_extended requires budget>=1.25 and beyond>0. Wording thresholds0.50 and3ATR
do not independently veto anything. Rendering returns the original Hebrew text.
Insufficient daily/range/shape data returnsNone, distinct from a valid state
that is not extended. A missing deviation omits only its timeframe. Original
intraday correction-ignoring, exception and nonfinite numeric behavior remains;
a raw NaN deviation may exist, so this is not a JSON-safe observation exporter.

## Evidence boundary

The caller supplies the correct instrument, available-at time, current daily
prefix, full warmup/history and correction evidence. No source price offset is
applied, no current-day final OHLC is constructed or inferred, no GC/spot alias
is allowed by implication. Raw source methods do not certify these inputs.
The existing broker_shape_ok_at can implement the shape port with explicit
operation time, but neither its boolean nor source tags establish feed coverage.

Audit CLI: `python tools/check_stretch_source_parity.py --source-root <parent-of-chart-desk>`.
It checks literal pins, full ordered projection and actual range/strictEMA
dependencies without importing/executing retained source or runtime. A VERIFIED
result leaves replay/training readiness false; runtime construction does not
automatically run the auditor. Acceptance requires recorded independent review.

Remaining: causal feed binding, full revalidation and lifecycle/effects/caller,
other branches, approved economic simulation/data and model evaluation.
