# Task 3 brief

## Global Constraints

- Approved pinned source is authoritative; no invented thresholds, calendars, feeds or GC/spot equivalence.
- Observation cutoff is not decision time. No backdating maps or rewriting publication to force availability.
- Existing default APIs, validation and result/hash behavior remain unchanged.
- All readiness flags and public tradeable remain false; selected source pricing is not external market-watch admission or execution.
- No source/feed execution, real-data access/downloads, fitting, live changes, broker operations or deployment.
- Preserve dirty in-place branch; no commits, pushes, worktrees, cleanup or nested implementer agents.
- Main owns acceptance/master/README/AGENTS/tracker. Source Task2 can run alongside controller Task1 because their files are disjoint. Task3 depends on accepted1/2.
- Full objective remains B-I, not merely this producer. Outer market-watch windows/calendar/tracker/deduplication/arbitration remain explicit next work, never silently considered done.

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

- [ ] Write failing real base/calendar/correction/map -> producer tests first.
  Synthetic M5/M15 same-confirmation opposite setups selectM5; newerM15 wins;
  onlyoneTF available; older fresh event with latestnonsignalbar; aged370 accepts,
  370+microsecond rejects; publicationbetweenclose/T accepted only atpublication.
  Current map timestamps remainT while eventconfirmed earlier; old detector
  guard remains unchanged. Exact source plan/refusal and featuretimestamps.
- [ ] Cover full original internal correction-gate matrix, missingdaily, optional
  failures, no candidates vs unavailable, warmup/volumeabsence/allzero/overflow,
  future price/correction and unusedmapfallback invariance, identity/duplicates/
  unsupportedGC, repeatdecision IDs vs event IDs, immutable outputs, nosends/
  labels/readiness. Use the real source math; do not mock map/detector/pricer.
- [ ] Run python -m pytest tests/tree_replay/test_reversal_producer.py -q --tb=short
  RED/GREEN; rerun old reversal/pricing tests for helper default compatibility.
  Independent task review required, then all source audits and full integration
  tests/tree_replay tests/tree_spec tests/data_foundation/test_sessions.py; broad
  python -m pytest -q --ignore-glob='*validator*' --tb=short. Explicitly record
  legacy validator exclusion; final combined review and durable acceptance.
- [ ] Update master/tracker/AGENTS/README after verification; keep outer admission,
  other branches/memory/simulation/dataset/models/evaluation and human gates open.
