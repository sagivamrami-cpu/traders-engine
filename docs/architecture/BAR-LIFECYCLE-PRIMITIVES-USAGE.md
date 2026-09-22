# Original bar geometry and movement proof

Private offline projections of chart-desk at commit
68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9. Contract:
BAR-LIFECYCLE-PRIMITIVES-CONTRACT.md. These are source primitives, not a public
historical replay engine, execution simulator or training-data generator.

`_vendor.lifecycle_bars` exposes the five original position-window functions.
The supplied frame and source trade row remain caller-owned. Pending touch is
strictly after send; OPEN/filled_ts selection and include_fill_bar differ as in
the source. A included fill bar contributes adverse but not favourable extremes.
Do not apply these raw helpers to unvalidated or future tape and infer causality.
Original exception handling remains: for example an empty OPEN frame with a
filled timestamp can raise ValueError in position_bars, while _fill_on_tape
catches invalid input and returns None.

`_vendor.desk_success.DeskSuccess(source)` requires explicit clock ports:

```python
class ClockPorts:
    def __init__(self, replay_clock):
        self.clock = replay_clock
    def now_epoch(self):
        return self.clock.now.timestamp()
    def now_utc(self):
        return self.clock.now
```

Both must refer to the same operation clock; now_utc returns an aware UTC
datetime. There is no wall-clock fallback or implicit integration with the
admission context. The source's as_of truthiness and numeric behavior are kept.

Methods: reached, observe, observe_bars, classification, stop_note. The module
retains minimum(symbol), VERSION and FLOOR. observe requires caller-certified
post-fill ordering and venue; it does not establish either from an arbitrary
price. observe_bars uses actual position_bars(include_fill_bar=True), excludes
future timestamps, the fill bar from favourable movement, and the first stop
bar and all later bars. The proof's observed/detected times are operation times,
not inferred intrabar crossings. Explicit now_utc avoids a rounded epoch cutoff.

Only minimum_success is added to an eligible trade by observe. Proof identity,
symbol, minimum distance, allowed evidence tag and source/resolved chronology
must validate. A valid proof stays sticky even if the trade later stops; it is
not a profitable-trade label. Original stop, targets and advisory state remain
unchanged. Advice to move a stop does not execute a move. Source classification
can use a caller measurement, which is not independently certified history.

The complete original pure lifecycle_voice preserves identity-first messages
and instrument units needed by later message parsers. No notifications are sent.
audited_classification and its external historical-report dependencies are not
included. Inherited pricing/canonical-symbol calculations remain original.

Verification uses hand-derived real pandas/ReplayClock cases, source AST audit
and independent review. Current scope leaves causal lifecycle feed binding,
revalidation, independent claim verification, stateful resolver/caller and
economic outcomes/dataset/model work open. Component acceptance is recorded in
agent-exchange/status, never inferred from this usage file or green tests alone.
