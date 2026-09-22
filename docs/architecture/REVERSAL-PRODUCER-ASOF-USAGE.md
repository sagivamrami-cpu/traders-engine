# Decision-time reversal producer

`trading_system.tree_replay.reversal_producer.find_reversal_asof` joins the
accepted closed-base-prefix frames and historical map to the original
`find_at` implementation pinned at
`68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`.
Schema and calculation version: `tree-reversal-producer-asof-v1`.

This is an offline internal producer evaluation. Source selection and pricing
do not establish market-watch admission, a notification, execution or a label.

## Typed inputs

```python
from trading_system.tree_replay.reversal_producer import (
    ReversalFrameRequest,
    find_reversal_asof,
)

# Frames, corrections, calendars and age policies are explicit supplied inputs.
# No feed is executed and no calendar, threshold or correction is inferred.
request_m5 = ReversalFrameRequest(
    frame=frame_m5,
    correction=correction_m5,
    max_correction_age_seconds=correction_age_policy,
)
result = find_reversal_asof(
    snapshot_id=snapshot_id,
    instrument="OANDA:XAUUSD",
    decision_time=decision_time,
    map_requests=map_requests,
    reversal_requests=(request_m5,),
)
```

`ReversalFrameRequest` is a frozen, keyword-only dataclass containing an exact
`FrameSpec`, a `CorrectionEvidence | None`, and a native nonnegative integer
correction-age policy. Its `timeframe` property comes from the frame and must
be `5m` or `15m`; its `lookback_days` property is fixed at `10`. Zero age means
only evidence observed at the same instant can pass freshness.

The two request collections must be tuples of exact `MapFrameRequest` and
`ReversalFrameRequest` objects, respectively. Identities, correction association,
map request keys, producer timeframes, and unique frame IDs across both
collections are checked before any lazy source call, including unused bindings.
Malformed structural inputs raise `ValueError`. All timestamps must be aware
and microsecond-exact. Frame/bar/calendar validation remains owned by the
accepted typed contracts.

Only the exact instruments in `pricing.SUPPORTED_INSTRUMENTS` can reach source
pricing: `OANDA:XAUUSD`, `OANDA:NAS100USD`, `BINANCE:BTCUSDT`. A structurally valid
unsupported instrument returns `BLOCKED / PRODUCER_UNSUPPORTED_INSTRUMENT`.
GC receives no spot alias or inherited spot band.

## Clock and selection semantics

Both producer frames and the real historical map use `closed_base_prefix=True`
at actual decision time T. Prices use published, completed base observations;
metadata, correction freshness, publication and source gates use actual T.
Publication between a bar close and T is eligible only after it occurs.

The map bridge reconstructs original source `NamedLevel` objects and its daily
`Correction` from the available map assessment. A blocked map is passed to the
original find veto as empty levels / missing correction; its full report remains
in the result. There is no caller-provided computed map or gate boolean.

Original find performs the daily gate and requests M5 then M15, each with
lookback 10. Missing/unverified intraday corrections and intraday `source=none`
are skipped by the original source. The daily gate only rejects missing or
unverified correction (or empty levels); a verified daily `source=none` is not
an extra blanket veto. Broker-shape gates inside map construction remain the
map's original separate rules.

The detector seam passes its actual timeframe, T and source freshness bound
`370.0` unchanged to the real detector. All returned events are retained.
Original find selects the newest confirmation, with M5 on a tie, and calls the
original pricer only for that winner. A newer refused plan is never replaced
with an older paying plan. An older fresh event can survive a later nonsignal
bar. A forming target row never becomes a completed confirmation.

Completed target rows require nonmissing volume and at least one positive
volume; otherwise that timeframe fetch records `VOLUME_UNAVAILABLE`. Zero
completed target rows, or fewer than 12 valid completed rows, reach the actual
detector and record `WARMUP`. Forming-row volume does not veto completed history.
No volume is manufactured. The accepted numeric overflow validator is reused.
Unexpected frame, post-fetch index/volume, detector or pricing calculations
produce blocked diagnostics with their stage and exception type, including
exceptions that original find would otherwise catch and skip.

The candidate's original `confirmed_at`, vector time and confirmation-open
time are preserved. Its feature snapshot and pricing snapshot observe and
become available at T, as does the current map snapshot. Considering an earlier
pattern at T does not claim that the current map or selected decision existed
at that earlier confirmation.

The old `detect_reversals_asof` and `price_reversals_asof` defaults are unchanged.
Their newest-confirmation behavior and `LEVELS_AFTER_CONFIRMATION` guard remain.
The only shared-helper extension is optional `_candidate_snapshot(observed_at=None)`;
omitting it preserves the original event confirmation observation time exactly.

## Results and evidence

| Status | Meaning |
| --- | --- |
| `BLOCKED` | Required map unavailable, unsupported exact instrument, or calculation failure. |
| `NO_SELECTION_INPUTS_UNAVAILABLE` | No source choice and a needed timeframe input was unavailable. |
| `NO_CANDIDATE` | Evaluated source gates/detectors produced no selection; inspect gate/warmup reasons. |
| `PRODUCER_SELECTED_UNADMITTED` | An actual source-selected event and plan, including a refused plan. |

`candidates` contains every event returned by actual detector calls. Only the
source winner has `source_plan` and `pricing_snapshot`; others are
`pricing_status=NOT_SELECTED`. The selected pricing status is
`PRICE_ACCEPTED_UNADMITTED` or `PRICE_REFUSED`. `source_plan` preserves original
entry zone, stop, ATR, risk, targets, obstacles, refusal, reasons and warnings.
Its `source_tradeable` is source pricing evidence only. Public `tradeable`,
`ready_for_replay` and `ready_for_training` remain false.

`selected` is a detached copy of the selected candidate. Inputs are immutable;
outputs are ordinary JSON-compatible dictionaries with no mutable cross-call
state. Mutating a returned selected snapshot cannot modify the traced candidate
or a later evaluation.

`map_report` retains the original map, fetch and broker-shape traces.
Producer `fetch_trace` includes actual correction assessments, frame hashes,
price/publication clocks, fetch blockers and a descriptive `producer_gate` when
an assessed correction was returned. Original find, rather than this trace,
still applies the gate. `detection_trace` records actual calls, closed-row counts,
reasons and candidate IDs. Producer `shape_trace` is empty when original find
makes no broker-shape call; map shape calls live inside `map_report`.
One unavailable timeframe does not veto a selection from the other. Its
coverage failure remains in the fetch trace.

Original episode IDs remain in `source_event_id`. `candidate_id` hashes source
commit, per-timeframe producer, source event ID and confirmation time, allowing
repeated consideration to be grouped without merging the M5/M15 candidates.
`decision_id` hashes this evaluation before adding the ID/hash fields, with the
`reversal-decision:` prefix. It changes with T, snapshot identity or consumed
evidence. `evaluation_sha256` is SHA-256 of the complete canonical JSON result
excluding that hash itself (`sort_keys=True`, separators `(',', ':')`,
`allow_nan=False`). Available evidence is consumed lazily: unused map fallback
payloads, future price bars and unavailable correction payloads do not enter
the evaluation. Calendar and metadata policies retain their accepted contracts.

## Scope and verification

The `_OfflineSource` trace, error and exception interfaces are deliberately
shared package-internal dependencies, not a second public generic-feed API.
Source math is delegated to the accepted vendor sidecars; runtime evaluation
does not run source parity audits.

Every result preserves these missing stages verbatim:

- `outer_market_watch_admission`
- `tracker_episode_state`
- `cross_producer_arbitration`
- `execution_and_outcomes`
- `full_tree_dataset_training`

The audited pure source `conflicts` helper does not constitute external
arbitration. Full B-I work, other producers, memory, simulation, datasets,
models and human approval boundaries remain open. This adapter does not read
real data, send messages, fit models, operate brokers, or change live behavior.

Focused tests:

```text
python -m pytest tests/tree_replay/test_reversal_producer.py -q --tb=short
python -m pytest tests/tree_replay/test_reversal.py tests/tree_replay/test_pricing.py -q --tb=short
```

The implementation worker runs these focused tests. Independent review, source
audits, broad integration and durable acceptance belong to the parent controller.
See [producer source contract](REVERSAL-PRODUCER-SOURCE-CONTRACT.md),
[closed prefix usage](CLOSED-BASE-PREFIX-USAGE.md) and
[historical map usage](HISTORICAL-LEVELMAP-USAGE.md).
