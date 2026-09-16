# GC Order Flow sidecar for XAUUSD tree evidence

## What this component is

`CME:GC` from `DATABENTO/GLBX.MDP3` can now be represented as an explicit,
closed-minute Order Flow context for a decision whose price/trade identity is
`OANDA:XAUUSD`. It is a sidecar: the current pinned `TreeReader` has no Order
Flow input port, so this component does not change a tree decision, alert,
entry, stop, direction, execution or P&L.

## Safe caller flow

1. Load the pinned policy from
   `configs/data/xauusd-gc-crossmarket-order-flow-context.yaml`.
2. Supply GC rows privately as `GcFlowMinute` objects. Each row has UTC
   `minute_start`, its source `available_at`, and only `volume`, `delta`, and
   `trades`. The caller also supplies archive digest and observed coverage.
3. Call `build_cross_market_flow_context` with the same decision time as a
   `FullTreePass` and an explicit `window_start`. There is no default window
   and no implied feature threshold.
4. Bind the returned `CrossMarketFlowContext` with
   `FullTreeCrossMarketContextRecord.capture(bundle, pass_id, context)`.
5. Store/report only `record.commitment()` or
   `FullTreeCrossMarketContextBaseline.capture(bundle, (record,))`. Those
   values contain provenance, timing, availability and content commitments,
   not raw flow values.

```python
policy = CrossMarketFlowPolicy.load(POLICY_PATH)
source = CrossMarketFlowInput(
    policy=policy,
    archive_sha256=policy.archive_sha256,
    coverage_start=first_minute,
    coverage_end=last_minute_end,
    minutes=caller_supplied_gc_minutes,
)
context = build_cross_market_flow_context(
    source,
    decision_time=tree_pass.decision_time,
    window_start=declared_window_start,
)
record = FullTreeCrossMarketContextRecord.capture(bundle, tree_pass.pass_id, context)
public_commitment = record.commitment()
```

## Fail-closed conditions

- The target must be `OANDA:XAUUSD`, source must be `CME:GC`, archive digest
  must match the approved policy, and the flow source remains separately
  labelled.
- A minute is eligible only after its one-minute interval has closed and it is
  available at the source. Any gap, duplicate, invalid order, non-finite value,
  delayed row, missing coverage, or overlap with the 2017 damaged interval is
  an `UNAVAILABLE` context with no numeric values.
- No GC price/OHLC, CVD, cumulative carry, interpolation, fill, zero, or
  XAUUSD fallback is supported.

## Deliberate non-claims

This component is not historical source acquisition. It does not establish
complete OANDA history, historical news/options coverage, economic labels, an
outcome dataset, model training, model promotion, live trading, broker
execution, capital allocation or deployment. An explicitly approved future
tree-branch interface is required before this context can affect tree logic.
