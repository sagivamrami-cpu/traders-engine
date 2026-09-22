# Causal admission frame ports

`trading_system.tree_replay.admission_frames` binds supplied historical bars,
calendars and correction evidence to the original source matrix and tracker
frame reads. It has no filesystem, network, live clock, quote or state provider.
See ADMISSION-FRAME-BINDING-CONTRACT.md and current exchange status for acceptance.

## Inputs and use

```python
from trading_system.tree_replay.admission_frames import (
    AdmissionFrameRequest, AdmissionFrameSource,
)

binding = AdmissionFrameRequest(
    timeframe="15m", lookback_days=55, frame=frame_spec,
    correction=correction_evidence, max_correction_age_seconds=60,
)
source = AdmissionFrameSource(
    instrument="OANDA:XAUUSD", decision_time=historical_decision,
    requests=(binding,),
)
view = source.read_symbol("OANDA:XAUUSD", ("15m",))["15m"]
```

The example's correction-age policy is illustrative and explicitly supplied,
not a new source trading threshold. Complete callers must supply every request
they need. Supported keys are4h240,1h240,30m90,15m55,5m55 and15m5; the two15m
histories have separate identities. Exact supported instruments are the existing
OANDA:XAUUSD, OANDA:NAS100USD and BINANCE:BTCUSDT, with no GC/spot or bare alias.
Requests are frozen records in an exact tuple, with matching exact FrameSpec/
CorrectionEvidence types, unique keys/frame IDs and explicit age policy.

`fetch_corrected(symbol,timeframe,lookback_days)` returns a newly built DataFrame
and Correction through the accepted `_OfflineSource` machinery. `read_symbol`
defaults to4h/1h/15m/5m and retains supplied order, original LOOKBACK, conditional
Correction.render and actual source read_frame. Failure stops the sequence; it
does not return a partial dictionary. A known forming higher-timeframe row made
from available closed base bars remains in the matrix, unlike detector-only
closed-target filtering. The decision clock remains actualT.

## Missing data, provenance and ownership

Missing/future/late/stale correction evidence and missing expected bars raise
with retained `fetch_trace`. An assessed unverified or source-none Correction
still reaches the matrix, as in the source. The matrix has no producer-style
quality veto. Requested days do not certify delivered days: original TV/MT5
source paths return full loaded history. No minimum-day gate, truncation, proxy,
backfill or offset is added. Supplied history_start, rows and calendar remain
the actual seed evidence and must be certified separately for real-data replay.

`matrix_trace` records each attempted timeframe, fetch start index, status,
blocker and exception type. It remains visible if tracker catches a failure and
returns None or defaults thesis to held. Callers must inspect both fetch and
matrix traces before claiming complete historical decisions. A fetch index on a
failure before fetching denotes the insertion position, not an existing row.
No report/readiness/hash API is implied by this input provider.

The provider is local mutable execution context for one instrument/decision;
it is not a serialized checkpoint or security capability. Returned frames,
corrections and views are freshly built, and changing one does not alter later
reads. Repeated calls remain visible in traces; there is no cache. Do not mutate
provider internals or traces to supply evidence for another decision.

Original numerical quirks are retained. The constant-price test returns net
-41.25, including the known source VWAP NaN-to-short100 behavior. These are
source descriptive scores, not probabilities, economic outcomes or a policy fix.

## Verification and unfinished work

Tests cover all six keys, original numerical readings/order, differing15m
histories, rising prices, correction availability versus source flags, failures,
forming target rows and delayed publication, future input exclusion, exact
validation, mutation isolation and real tracker bias/thesis/post-stop consumers.
A combined actual selected-Plan -> causal matrix -> original record test retains
the report and source broker-unverified OPEN. Its memory/quote ports remain
controlled synthetic inputs. Individual timeframe seeds and producer fixtures
are supplied independently; same decision time is not proof of one coherent
historical feed or full lookback. Full-data assembly must establish that lineage.

```text
python -m pytest tests/tree_replay/test_admission_frames.py tests/tree_replay/test_admission_calculations.py tests/tree_replay/test_tracker_admission.py tests/tree_replay/test_reversal_handoff.py tests/tree_replay/test_frames.py tests/tree_replay/test_corrections.py -q --tb=short
python tools/check_admission_source_parity.py --source-root <retained-source-parent>
```

The source audit verifies inherited formula projections; constructing a provider
does not automatically execute it. Review also checks this thin read_tf binding.
Full source state/locks/save, causal quotes and byte-faithful raw-log prefixes,
heterogeneous watch memory, branch ordering, lifecycle and other producers remain.
There are no fills, outcomes, dataset, trained model or live-trading readiness.

Component accepted after independent task/final reviews, including the600-row
regression for preservation of history older than requested lookback. Fresh
436combined tests and sourceaudit10 passed (counts overlap earlier runs).
Acceptance: agent-exchange/status/2026-09-09T154823Z-codex-admission-frames.md.
