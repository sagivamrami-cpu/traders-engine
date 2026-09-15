# CME GC Order Flow as XAUUSD context — design

**Status:** approved business/data semantics; awaiting team review before an
implementation plan.

## Purpose

Make the project's genuine CME Gold futures Order Flow available as a causal,
cross-market context for the existing XAUUSD tree. The goal is to give the tree
the order-flow evidence Sagiv considers meaningful without misrepresenting the
futures price as the spot/CFD price it trades.

## Chosen design

```
XAUUSD price tree: OANDA:XAUUSD ── price, levels, trade plan, economics ──► candidate
                                                                         │
CME futures tape: Databento CME:GC ── volume/delta/trades at closed 1m ─┤
                                                                         ▼
                                                           context snapshot at T
```

The candidate's trade identity is always `OANDA:XAUUSD`. Every flow field has
an independent provenance identity: `CME:GC`, `DATABENTO/GLBX.MDP3`, selected
member `gc/GCext_of_1m.parquet`.

## Input contract

The existing archive manifest is the source identity contract:

- GC 1m fields allowed: `volume`, `delta`, `trades`.
- Each source timestamp identifies the minute start. That observation becomes
  eligible at `minute_start + 60 seconds`.
- Use UTC throughout.
- Exclude the half-open damaged window `[2017-01-01, 2017-06-01)`.
- Do not consume archived `cvd`, recompute CVD, carry cumulative state across
  folds, infer missing minutes, or use an unapproved field.
- The raw archive remains outside the repository and agent exchange. The
  adapter receives caller-supplied data with archive/member digest and coverage
  metadata, as does the current evidence-capture design.

## Temporal join

For an XAUUSD decision at time T:

1. Identify the closed GC 1m rows with `minute_start + 60 seconds <= T`.
2. Apply the damaged-era mask before calculating any feature.
3. Aggregate only the closed rows in the declared backward window.
4. Publish the result with `observed_at` equal to the last used GC minute end
   and `available_at` equal to the same end unless a source-specific delayed
   availability record says otherwise.
5. If any required minute/window is unavailable, return a typed unavailable
   result with the source and coverage reason. Do not fill it with XAUUSD bars,
   the latest GC value, zero or a future observation.

The first implementation will expose raw-window quantities (volume, delta,
trades) plus explicitly named ratios only where the denominator is positive.
It will not claim a new threshold or signal. The original tree/feature layer
continues to decide how an available or unavailable context affects a candidate.

## Boundaries

| Allowed | Forbidden |
| --- | --- |
| GC flow as a separate context feature | GC OHLC as XAUUSD price or level |
| Closed-minute causal aggregation | Current/forming/future GC minute |
| Source and target identities on every output | `GC` relabelled as `OANDA:XAUUSD` |
| Explicit unavailable/coverage reason | Imputed value, price offset or stitched proxy |
| Research coverage accounting | Any fill, P&L, model or live-trading claim |

## Components to add

1. **Cross-market flow contract**: immutable input/value records holding target
   and source identities, minute timing, digest, coverage and false readiness.
2. **Causal aggregator**: caller-supplied GC minute frame -> one context result
   at XAUUSD decision T. It knows neither XAUUSD prices nor a trade plan.
3. **Full-tree source adapter**: maps the typed context to the tree's Order
   Flow port while retaining missing/late semantics and trace operation order.
4. **Coverage ledger**: reports the joint XAUUSD/GC interval and all exclusions
   for complete-information research. It does not alter live-tree vetoes.

The adapter must be additive. Existing Dukascopy-derived flow and the current
tree remain unchanged until the new path has source tests, replay evidence and
an explicit comparison.

## Tests and acceptance

Tests will prove:

- a decision cannot consume a GC minute that ends after T;
- minute-start versus minute-end boundary behavior;
- damaged 2017 row exclusion;
- missing, gap, nonfinite and wrong-identity input remain unavailable;
- output never contains XAUUSD prices or transforms a GC price;
- source and target provenance persist through full-tree capture/replay;
- checkpoint/replay at the same T yields the same payload-free commitment;
- aggregate coverage lists an excluded span rather than manufacturing rows.

Acceptance requires the new focused suite, current full-tree capture/provider
suite, static source audits and independent code review. It does not establish
historical OANDA price coverage, economics, an outcome dataset or model
readiness.

## Dependencies and remaining inputs

- The `OANDA:XAUUSD` price source profile still needs a source-faithful
  historical input before whole-tree replay can start.
- Current local GC archive identity is pinned and has 1m coverage through
  2026-07-17T20:59Z; actual adapter construction must re-validate digest and
  source availability against the approved input contract.
- Options and historical news coverage remain independent requirements for the
  full-information research cohort.

## Design self-review

No threshold, price conversion, fill/economic assertion or new live behavior is
specified. Source/target identities, causality, damage masking and unavailable
behavior are explicit. The design is limited to the Order Flow context path and
does not alter the selected OANDA price identity.
