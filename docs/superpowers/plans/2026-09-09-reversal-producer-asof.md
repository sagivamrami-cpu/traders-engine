# Original reversal producer at historical decision time

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Preserve completed gates across continuations.

**Goal:** Run the original reversal find/provenance/selection/pricing path at actual historical decision time, including fresh older confirmations.

**Architecture:** Add opt-in closed-base-prefix clocks without changing strict default interfaces. Port find/conflicts with exact AST-audited dependency injection. Bind actual causal maps/frames and correction evidence to that source path and retain the full decision trace.

**Tech Stack:** Existing Python/pandas/numpy/pytest and text-only AST audits; no new dependency.

**Spec:** docs/architecture/REVERSAL-PRODUCER-SOURCE-CONTRACT.md and approved master TR-TREE-OUTCOME-LEARNING-PLAN-2026-09-08.md.

## Global Constraints

- Approved pinned source is authoritative; no invented thresholds, calendars, feeds or GC/spot equivalence.
- Observation cutoff is not decision time. No backdating maps or rewriting publication to force availability.
- Existing default APIs, validation and result/hash behavior remain unchanged.
- All readiness flags and public tradeable remain false; selected source pricing is not external market-watch admission or execution.
- No source/feed execution, real-data access/downloads, fitting, live changes, broker operations or deployment.
- Preserve dirty in-place branch; no commits, pushes, worktrees, cleanup or nested implementer agents.
- Main owns acceptance/master/README/AGENTS/tracker. Source Task2 can run alongside controller Task1 because their files are disjoint. Task3 depends on accepted1/2.
- Full objective remains B-I, not merely this producer. Outer market-watch windows/calendar/tracker/deduplication/arbitration remain explicit next work, never silently considered done.

## Task 1: Separate observation cutoff from actual decision clock

Owner: controller. Modify periods.py, frames.py and levelmap.py under trading_system/tree_replay/; create tests/tree_replay/test_closed_prefix.py and docs/architecture/CLOSED-BASE-PREFIX-USAGE.md. Do not alter existing default test assertions.

Interfaces add keyword-only closed_base_prefix:bool=False to aggregate_daily_asof,
build_frame_asof and build_levelmap_asof. Exact bool required (0/1 rejected).
_OfflineSource gains a final optional closed_base_prefix=False argument and passes
it into build_frame_asof; existing three-argument use remains valid. FrameSpec
and MapFrameRequest constructors are unchanged.

When false, retain original strict grid rejection, schema/calculation versions,
fields and hashes. When true, permit arbitrary aware microsecond T. Use UTC
epoch-aligned floor of min(T,period.end) for daily observation; frame cutoff is
floor(T/base_step). Publication/metadata/freshness use actual T, never the floor.
No caller-selectable earlier price cutoff that can hide a missing expected bar.

Daily period boundaries remain base aligned. Expected trading bars end at the
derived cutoff; all required closed history remains mandatory. T can lie after
period end and late-published completed bars remain usable at T. Current-period
selection/ownership in the frame builder uses actual T, never yesterday. Empty
current prefixes block as before. Frame calendar coverage remains required through
actual T. Intraday grid-fragment checks stop at derived cutoff; the existing
select_session_bars receives actual T and naturally requires every whole closed
base bar while checking real publication and age. No partial bar is fabricated.

Prefix-only versions/fields:
- period schema daily-period-prefix-asof-v1; calculation closed-lower-bars-daily-period-prefix-v1.
- frame schema historical-frame-prefix-asof-v1; calculation closed-base-frame-prefix-v1.
- map schema/calculation historical-levelmap-prefix-asof-v1; generated snapshot version matches.
- period/frame add observation_cutoff in canonical result/evidence only in prefix
  mode. Map trace available frame includes that cutoff only in prefix mode.
- Prefix policy participates via version/fields in hashes, even at a grid-aligned T.

Implementation arithmetic (shared small helper is permitted in periods.py):
```python
epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
cutoff = epoch + ((min(decision_time, period.closed_at)-epoch)//step)*step
# Eligibility remains bar.available_at <= decision_time, not <= cutoff.
```

- [x] Write tests first. Literal two5m bars O100/H103/L99/C102 and O102/H107/L101/C106, at T00:10:30 with second publication00:10:20: expected O100/H107/L99/C106. Expected observation00:10, publication00:10:20 and cutoff00:10. A third final OHLC1000 bar closing00:15 is excluded. At00:10:19 second bar is missing and prices withheld; at exact publication it becomes usable. Never use a calculator as expected oracle.
- [x] Verify strict default still rejects off-grid T; explicitFalse equals default byte-for-byte. Capture default fixture hashes before edits and assert they remain identical. True/False/0/1/None/string policy cases; naive/nanosecond T rejected; zero-age freshness checked against real T; exact370 and370+microsecond freshness where policies allow.
- [x] Cover daily current rollover/no observations; missing expected history; known closures vs missing; metadata published between cutoff and T; calendar coverage ending at cutoff but before T;23/25h periods;1h/4h forming prefixes; future bar/period extension invariance; source session end at actual clock with old prices; delayed bar reappears only at publication. Test all three public interfaces and actual map prefix output, not helper-only arithmetic.
- [x] Run python -m pytest tests/tree_replay/test_closed_prefix.py -q --tb=short for RED, implement and GREEN; then existing test_periods.py/test_frames.py/test_levelmap.py suites. Document versions/default compatibility and unsupported open-only/base-partial observations. Independent task review required.

## Task 2: Exact original find and conflicts source sidecar

Owner: one source worker; independent of Task1. Create _vendor/reversal_producer.py,
tools/check_reversal_producer_source_parity.py, configs/trees/reversal-producer-contracts.json,
tests/tree_replay/test_reversal_producer_source.py, docs/architecture/REVERSAL-PRODUCER-SOURCE-USAGE.md.

Source root/commit/blob exactly as named in the source contract. Read as text only.
Retain original full find and conflicts. Existing detector, constants, dataclass,
normalization and build_plan are imported, not copied or changed. Allowed imports
in this exact order:
```python
from __future__ import annotations
import pandas as pd
from .level_reversal import Reversal, _utc, LIVE_MAX_AGE_S
from .reversal_pricing import build_plan
from . import pricing as tradeplan
```
Adapt find to:
```python
def find_at(symbol: str, *, decision_time, source, map_source, detector):
    # Original docstring, then these bindings:
    basis = source
    levelmap = map_source
    detect_frame = detector
    now = _utc(decision_time)
    # Original remaining body exactly, including levelmap.build(symbol).
```
The detector argument is an internal instrumentation seam; public callers never
provide it. It must delegate to the accepted real detector. map_source.build
returns actual levels/correction at the same T. All other statements, guards,
request10,370 freshness, sort order, exceptions and selected-only pricing remain
exact. conflicts is copied unchanged, not falsely described as outer admission.

New audit uses fixed independent commit/blob, exact whole manifest and ordered
module AST. Prove original signature/clock and binding-name preconditions before
transformation. Verify exactly one baseline chart-desk pin. Invoke existing full
check_levelmap_source_parity (inherits all calculation dependencies) and require
true subset/empty blockers/false readiness. Independently seal accepted map
manifest canonical JSON hash; do not trust a mutated manifest. Expected errors
become BLOCKED reports; source/vendor never executes in auditing. CLI rootarg >
TR_CHARTDESK_SOURCE_ROOT > retained default; success0, missing/mutation2.

- [x] TDD source behavior using real detector/pricer and explicit offline feed/map
  fixtures: no map/none/unverified daily gates; valid proxy/replay daily not
  blanket-vetoed; bar none/unverified/source=none skip; request5m then15m/10;
  per-TF fetch exceptions continue; literal M5/M15 tie, newerM15 vs olderM5;
  older fresh confirmation when latestbar has no signal;370 inclusive and one
  microsecond older excluded; original per-episode/nearest-level behavior.
- [x] Test newest refused plan is still selected, not replaced with an older
  accepted plan; source conflicts exact same/opposite/empty directions, same/
  different symbol and tradeability. Hand-derived real input fixtures; no
  mocked detector/pricer or formula outputs. Instrumentation may record calls
  while delegating real math. Low-level supplied map fixtures are permitted.
- [x] Mutation tests relocate source/vendor/manifests; changedsignature/clock/
  binding/guard/request/freshness/order/imports/extra statements/sourceblob/
  baseline duplicates/false-vs0/dependency drift/missing root all rejected.
  Do not modify production pins or existing auditors. Verify prefix-clock Task1
  wrappers are not part of the source formula audit, and no accepted dependency
  is modified by this worker.
- [x] Run python -m pytest tests/tree_replay/test_reversal_producer_source.py -q
  --tb=short RED/GREEN and python tools/check_reversal_producer_source_parity.py.
  Report self-review and evidence; independent task review before acceptance.

## Task 3: Real as-of producer evaluation and evidence

Depends on accepted1/2. Create trading_system/tree_replay/reversal_producer.py,
tests/tree_replay/test_reversal_producer.py, docs/architecture/REVERSAL-PRODUCER-ASOF-USAGE.md.
Narrowly modify reversal._candidate_snapshot to add optional observed_at=None;
default keeps existing event.confirmed_at exactly, new producer passes actual T.
No old detector/pricer public contract or guard changes.

Interfaces:
```python
@dataclass(frozen=True, kw_only=True)
class ReversalFrameRequest:
    frame: FrameSpec                 # timeframe5m or15m
    correction: CorrectionEvidence | None
    max_correction_age_seconds: int
    @property
    def timeframe(self): return self.frame.timeframe
    @property
    def lookback_days(self): return 10

def find_reversal_asof(*, snapshot_id: str, instrument: str,
                      decision_time: datetime,
                      map_requests: tuple[MapFrameRequest, ...],
                      reversal_requests: tuple[ReversalFrameRequest, ...]) -> dict: ...
```
Validate exact request types/identities, unique timeframe and all map/producer
frame IDs, correction association and native nonnegative policy. Timestamp aware
microsecond exact. Only pricing.SUPPORTED_INSTRUMENTS may reach source pricing;
unsupported exact instruments return BLOCKED/PRODUCER_UNSUPPORTED_INSTRUMENT,
never inherit spot bands. Malformed structural inputs raise ValueError.

Reuse levelmap._OfflineSource with closed_base_prefix=True for producer request
bindings (ReversalFrameRequest exposes its fixed request key). Its private trace
and exception interfaces are explicitly shared package-internal dependencies,
not a second public generic-feed API. Wrap fetch to retain successful frames
for pricing/vector evidence. Add producer_gate trace from actual correction
attributes; the copied find still makes the true selection, not that trace flag.
For detector history, require nonmissing and at least one positive volume on
closed target rows, and use existing _numeric_frame overflow validation. Mark
VOLUME_UNAVAILABLE fetch and skip unavailable TF, never fabricate volume. A
forming target row is not a completed confirmation; source detector's own
close filtering remains in force. WARMUP (<12closed rows) is traceable evaluated
insufficient history, not a losing trade. Unexpected numeric/calculation errors
block with type/stage diagnostic, never masquerade as a quiet market.

Map bridge build(symbol) computes actual build_levelmap_asof with prefixTrue at
T, reconstructs original source NamedLevel objects and daily source Correction
from its available assessment. No user-provided computed map, readiness or fake
source flag is accepted. Blocked map returns empty/None for original find veto,
with original report retained. All input identities validated before lazy calls.

Detector seam logs each actual call's timeframe/370/T, invokes real source
detect_frame with those same arguments and records all returned events. Source
find chooses newest/M5tie and calls original build_plan only for the winner.
Serialize its source plan with existing pricing._source_plan and entry_zone;
no re-selection based on plan profitability/refusal. Use real pvsra vector
evidence and existing _candidate_snapshot with observed_at=T, available_at=T.
Pricing snapshot also observes T. Keep original event confirmed_at/vector time
unchanged, even if earlier than current map observation. Decision at T is never
reported as a trade or signal known at that earlier confirmation.

Result schema/calculation tree-reversal-producer-asof-v1, source_commit, T,
snapshot_id and deterministic decision_id. Keep original per-episode source
event ID, per-TF candidate ID (sourcecommit/producer/sourceevent/confirmedtime),
all traced candidates and the selected one. Candidate IDs group repeated
consideration; decision_id/snapshot distinguish each evaluation. Canonical JSON
hash excludes itself and unused/future payloads. Include map report, fetch/shape/
detection traces and exact reasons for missing/vetoed/timeframe/warmup paths.

Statuses: BLOCKED for required map/unsupported/calculation errors;
NO_SELECTION_INPUTS_UNAVAILABLE when no source choice exists and needed TF input
was unavailable; NO_CANDIDATE when evaluated source gates/detectors yield none;
PRODUCER_SELECTED_UNADMITTED on an actual source-selected event/plan, even if
its pricing_status is PRICE_REFUSED. Otherwise selected pricing status is
PRICE_ACCEPTED_UNADMITTED. If oneTF was unavailable and another selected, retain
that partial coverage and original source selection, not a new global veto.
All public tradeable/readiness flags false. Keep missing_stages explicit:
outer_market_watch_admission, tracker_episode_state, cross_producer_arbitration,
execution_and_outcomes, full_tree_dataset_training. Pure source conflicts is
audited but not advertised as full external arbitration.

- [x] Write failing real base/calendar/correction/map -> producer tests first.
  Synthetic M5/M15 same-confirmation opposite setups selectM5; newerM15 wins;
  onlyoneTF available; older fresh event with latestnonsignalbar; aged370 accepts,
  370+microsecond rejects; publicationbetweenclose/T accepted only atpublication.
  Current map timestamps remainT while eventconfirmed earlier; old detector
  guard remains unchanged. Exact source plan/refusal and featuretimestamps.
- [x] Cover full original internal correction-gate matrix, missingdaily, optional
  failures, no candidates vs unavailable, warmup/volumeabsence/allzero/overflow,
  future price/correction and unusedmapfallback invariance, identity/duplicates/
  unsupportedGC, repeatdecision IDs vs event IDs, immutable outputs, nosends/
  labels/readiness. Use the real source math; do not mock map/detector/pricer.
- [x] Run python -m pytest tests/tree_replay/test_reversal_producer.py -q --tb=short
  RED/GREEN; rerun old reversal/pricing tests for helper default compatibility.
  Independent task review required, then all source audits and full integration
  tests/tree_replay tests/tree_spec tests/data_foundation/test_sessions.py; broad
  python -m pytest -q --ignore-glob='*validator*' --tb=short. Explicitly record
  legacy validator exclusion; final combined review and durable acceptance.
- [x] Update master/tracker/AGENTS/README after verification; keep outer admission,
  other branches/memory/simulation/dataset/models/evaluation and human gates open.
