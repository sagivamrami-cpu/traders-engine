# Causal admission frame-provider contract

Next mandatory part of approved master C after the selected-Plan handoff.
This is not a full tracker port implementation: state, locks/saves, quotes and
raw-log prefixes remain separate inputs. Source authority is pinned chart-desk
68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9. Read the latest frame-provider section
of MARKET-WATCH-ADMISSION-SOURCE-INTAKE.md before implementing.

## Exact interface

Create trading_system/tree_replay/admission_frames.py with:

- Frozen keyword-only AdmissionFrameRequest(timeframe:str, lookback_days:int,
  frame:FrameSpec, correction:CorrectionEvidence|None,
  max_correction_age_seconds:int). Supported pairs exactly4h240/1h240/30m90/
  15m55/5m55/15m5. Native types, matching timeframe/instrument/frame identity,
  nonnegative native correction-age integer. Revalidate identities before use.
- AdmissionFrameSource(*,instrument:str,decision_time:datetime,
  requests:tuple[AdmissionFrameRequest,...]). Exact supported producer instrument,
  aware microsecond-exact UTC decision, exact tuple/record/FrameSpec/correction
  types, unique request keys and frame IDs. No global state/provider or I/O.
- fetch_corrected(symbol,timeframe,lookback_days)->(DataFrame,Correction), using
  the accepted _OfflineSource causal construction in closed_base_prefix mode.
  Preserve input traces, correction assessment and exception recording. Do not
  weaken MapFrameRequest or copy the full generic frame builder into this file.
- read_symbol(symbol,tfs=("4h","1h","15m","5m"))->dict[str,TFView], with exact
  original order and LOOKBACK mapping from admission_matrix. Call fetch_corrected,
  then corr.render() if corr.show else None, then actual read_frame(df,tf,note).
  A failure aborts the comprehension-equivalent sequence, not a partial return.
- fetch_trace and matrix_trace remain instance-local. A matrix attempt records
  requested tf, starting fetch index, success or missing/calculation failure and
  exception type where applicable. A tracker catch cannot erase that evidence.
  No availability/feature hash API is added solely for this component.

Reuse the existing independently audited read_frame projection, not a rewritten
net score, supplied score or new tool weighting. No source audit is claimed merely
because this provider was constructed; run applicable parity tools at acceptance.
The enclosing final replay adapter still owns its report and readiness gate.

## Behavior and evidence boundaries

Construct at actual T, prices through closed base prefixes; do not filter out a
forming higher-timeframe row assembled from already available base bars. That
filter belongs to the reversal detector, not original matrix.read_tf. Record
source labels/bar_ts distinctly from price observation/publication cutoffs.

Missing/future/stale correction evidence is unavailable. Available assessed
unverified/source-none evidence still reaches the original matrix: it has no
producer-style veto. Preserve Correction.show/render and source numerical quirks.
An assessment of a supplied source is not independent historical feed certification.

LOOKBACK is the original request key, not guaranteed delivered days. Original
TV/MT5 sources return their entire loaded history; do not introduce a universal
minimum-day gate, trim rows to the requested days, backfill or silently change
warmup. FrameSpec.history_start, calendar and actual rows expose the supplied
seed. Before real-data replay, certify the selected feed/delivery/seed contract
separately; neither a request for240days nor a short synthetic fixture does so.

Every call constructs detached output so mutation of one returned frame/view
cannot affect a subsequent call. Repeated source reads stay observable in traces;
do not add caching that changes original dependency ordering. One instance is
bound to one exact instrument and decision. Unsupported symbol/timeframe/key
must fail descriptively without touching live sources. Trace failures at the
port even when an enclosing tracker would swallow them.

## Required tests

Use actual closed bars/calendars/FrameSpec/corrections, original read_frame and
actual TrackerAdmission higher-bias/thesis/post-stop consumers. Literal expected
values on hand-checked or characterized fixed fixtures; do not compute expected
net by calling the same code under test. Integration can use explicit test-only
memory/quote/log ports while delegating frame methods to this real provider.

Cover all six key pairs, both15m histories kept distinct, original requested tf
order, default tfs, missing early tf abort/no later reads, repeated calls and
output mutation isolation. Missing/late/future/stale correction and missing bars
must produce blocked traces; assessed unverified/source-none must be calculated.
Mid-target closed-base prefix must retain a forming row and original bar_ts;
future-only prices/publications cannot influence earlier readings. Include
incomplete supplied session history and unsupported GC identity without alias.
Controlled computation fault must survive tracker _higher_bias's returnNone in
provider traces. Validation errors preserve exact native types/microsecond time.

Positive integration proves actual tracker nets/thesis use this provider, not
test-supplied net booleans. It does not prove the full branch, watch-log generation,
quote provenance, advisory lifecycle, fill/exit or outcome label. Full master
requirements and explicit human real-data gates remain binding.
