# Historical level-map adapter

`trading_system.tree_replay.levelmap` binds accepted causal frame construction
and correction assessment to the accepted complete pinned source map graph.
It evaluates supplied synthetic/offline inputs at an explicit decision time.
`BUILT_UNADMITTED` is a calculated map, not producer admission, a candidate,
a fill, an outcome label, or completion of the tree/model plan.
`ready_for_replay`, `ready_for_training`, and `tradeable` are always false.

## Public interface

```python
from trading_system.tree_replay.levelmap import MapFrameRequest, build_levelmap_asof

daily_request = MapFrameRequest(
    timeframe="1d",
    lookback_days=400,
    frame=daily_frame_spec,       # accepted FrameSpec, not a DataFrame
    correction=daily_correction, # accepted CorrectionEvidence, or None
    max_correction_age_seconds=explicit_correction_age_budget,
)
result = build_levelmap_asof(
    instrument="OANDA:XAUUSD",
    decision_time=decision_time,
    requests=(daily_request,),
)
```

`MapFrameRequest` is frozen and keyword-only. Only these original request keys
are supported: `(1d,400)`, `(5m,3)`, `(1h,20)`, `(15m,20)`, `(1h,240)`,
`(4h,240)`. Lookbacks are native integers; the correction age budget is a
native nonnegative integer, including zero. Frame age policy comes from the
`FrameSpec`. Bool and floating-point policies are rejected.

Supply a tuple of requests with unique request keys and frame IDs. Frame
timeframes must match their requests. Every frame must match the exact map
instrument, and correction instrument/frame IDs must match their frame.
No symbol normalization or GC-to-OANDA mapping is performed. Invalid request
types, identities, policies, duplicate keys/IDs and invalid decision timestamps
raise `ValueError`; constructors retain their existing structural validation.
Even unused request identities are validated.

Read [historical frame inputs](HISTORICAL-FRAMES-USAGE.md) and
[correction evidence](CORRECTION-ASOF-USAGE.md) for the accepted constructors.
The source inventory and boundaries are in
[source graph usage](LEVELMAP-SOURCE-USAGE.md) and
[historical source contract](HISTORICAL-LEVELMAP-SOURCE-CONTRACT.md).

## Causal precision and source gates

Each actual source fetch reconstructs its frame at the same decision time T,
then calls `assess_correction_asof` with lookback zero to check temporal
availability. The preflight shape flag is evidence, not a universal admission
gate. Only an available frame and ASSESSED correction produce a fresh local
DataFrame and source `Correction`. Unknown input raises the adapter's private
`_DataUnavailable` exception at the original fetch boundary. No live fallback,
I/O, source feed import, mutable global feed/clock, or caller readiness flag is
used. Supplied OHLC is already on its attested basis; offsets are recorded but
never applied again.

The original graph retains its own family order, warmups, exception boundaries
and asymmetric correction rules. In particular:

- Daily input is required. Daily range shape uses the source's actual 20-day
  predicate; a proxy can still supply the families the original graph permits.
- Session opens use the source's exact bar/session and per-bar splice rules.
  A completed base bar must make the opening price known before it is exposed.
- PSY prefers `(1h,20)`. The graph tries `(15m,20)` after an available hourly
  frame fails its shape test. An hourly fetch exception exits the original PSY
  try block, so the fallback is not fetched in that case. Actual PSY shape
  calls use seven days.
- EMA fetches retain their source warmup checks and do not inherit a blanket
  broker-shape veto.

Supported precision is a completed base bar. A forming higher-timeframe row
contains only its published closed-base prefix, never final future OHLC.
Partly observed base bars and open-only ticks remain unsupported. Session
schedules, intraday grids, source daily labels and broker-period boundaries
are supplied attestations, not independent vendor/calendar certification.

## Result and evidence

`schema_version` and `calculation_version` are `historical-levelmap-asof-v1`.
The result records instrument, decision time, status, blocker, diagnostic,
levels, source omissions, correction evidence, fetch/shape traces and false
readiness/tradeability. `levels` preserves original `{name, price, kind}` order.
No invalid source level is silently removed: nonfinite/nonpositive prices or
an incompatible snapshot block the entire map. Unexpected uncaught source
calculation errors also block, with an exception-type diagnostic. Unexpected
frame/conversion errors block the map even if an optional source fetch caught
them. Diagnostics omit exception payloads that could expose unavailable input.

`REQUIRED_DAILY_INPUT_UNAVAILABLE` has no levels or snapshot, with the exact
unavailability reason in `fetch_trace`. Optional unavailability does not by
itself block the daily map. `source_missing` preserves source strings verbatim,
including source warmup and EMA fetch omissions. A built map does not imply
all families were available: source gates and short history can omit families,
and not every original omission has a source missing-string.

`fetch_trace` follows actual source request order, independent of supplied tuple
order. Each entry contains its key, frame ID, selected age policies, status and
blocker. Available frames contribute their accepted evaluation hash, row count,
actual price observation/publication times, and last-row source label/bounds/
forming state. Blocked frames contribute their blocker, not a hash of their
unavailable metadata. Correction preflight records the assessment and its hash;
unavailable correction payloads remain absent under the accepted assessment
contract. `level_correction` is the daily preflight assessment on a built map.

`shape_trace` records each actual source consumer call separately: fetch index,
frame ID, source lookback, T, result and the associated correction evidence hash.
The predicate is recomputed at T, rather than reusing the zero-day preflight
flag. Actual consumed frame/evidence hashes make dependency changes auditable.
Traces do not embed raw bar payloads.

`evaluation_sha256` hashes canonical JSON of the entire result excluding that
hash itself (sorted keys, compact separators, finite numbers). Only fetched
requests contribute policies/evidence. Valid unused fallback values and future
bar suffixes do not change the result/hash. Frame hashes retain the accepted
frame builder's supplied calendar/provenance identity; changing that attestation
is a dependency change, not merely appending future price bars.

## Consuming the snapshot

On a built map, `level_snapshot` is a JSON-compatible dictionary. Convert its
timestamps and named-level dictionaries to the existing immutable contracts:

```python
from datetime import datetime
from trading_system.tree_replay.levels import LevelSnapshot, NamedLevel

payload = dict(result["level_snapshot"])
payload["levels"] = tuple(NamedLevel(**level) for level in payload["levels"])
for key in ("observed_at", "available_at"):
    payload[key] = datetime.fromisoformat(payload[key].replace("Z", "+00:00"))
level_snapshot = LevelSnapshot(**payload)
```

Snapshot `observed_at` and `available_at` equal T. Source session membership and
splice eligibility can change at T without a newer price bar, so timestamping
the map at an older price close would misrepresent when its levels were known.
Actual price timestamps remain in the frame trace. Every consumed dependency
must already be available by T. Snapshot identity hashes its content and selected
dependency traces. Each level ID derives from name/kind/price, so adding/removing
another family does not shift IDs; repeated names at distinct prices remain
distinct. No enumeration-based level identity is used.

Pass this snapshot as `level_snapshot` to the accepted
`detect_reversals_asof` / `price_reversals_asof` wrappers with explicitly supplied
bar history and age policies. Their existing confirmation-time, instrument and
admission rules still apply. The synthetic integration test builds real map
levels, detects a real source reversal, and computes original source pricing
without hand-supplying price levels. A separate flat history proves the same
map can legitimately yield `NO_CANDIDATE`.

## Verification and remaining scope

Worker verification: `python -m pytest tests/tree_replay/test_levelmap.py -q --tb=short`.
Controller owns source audits, integration/broad suites and final acceptance;
the broad suite's legacy-validator exclusion must remain explicit in its result.
This adapter does not implement full producer find/admission/arbitration, the
state machine, execution simulation, datasets, training, evaluation or human
approval gates. No real-data access, source downloads, live alerts, broker
operations or deployment are part of this component.
