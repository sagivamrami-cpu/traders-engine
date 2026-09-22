# Original reversal producer: decision-time contract

Authority: approved master and pinned-repository decision2026-09-08. This is
engineering decomposition of that approved design, not a new trading policy.
Previous goal turn completed the historical-map core and made concrete progress.

## Source evidence

Read-only checkout: C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk.
Commit68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9, clean on inspection.
Git-verified blobs:chartdesk/level_reversal.py
7c0eee53d97a1ba9280626fdb2d20eba61b5aa1b; scripts/market_watch.py
f530fbe82cffbaf831c7a7725c7a9bf6143e6b8b. Source text was read, never executed.

find at level_reversal.py:269 builds a current map, vetoes empty levels or a
missing/unverified daily correction, then requests5m and15m with lookback10.
Fetch failures skip that timeframe. A missing/unverified/source=none bar
correction is skipped. It invokes the real detector with LIVE_MAX_AGE_S370.0
for each timeframe. All returned fresh candidates participate, including a
confirmation before the newest bar. Global choice is newest confirmation, M5
on an equal time. Only the selected event is priced; a refusal is not replaced
with an older more profitable-looking candidate. conflicts:294 checks a
tradeable reversal, exact symbol and opposite nonempty directions; it does not
independently establish freshness or whole-producer admission.

The older offline detect_reversals_asof intentionally evaluates only its newest
confirmation and requires levels observed by that confirmation. It remains a
valid distinct interface, but is not the full live find contract. A new producer
evaluation uses levels/data known at decision T; an older confirmation is a
historical pattern considered at T, not a claim that those levels were known at
confirmation. Keep confirmed_at, decision_time and feature availability separate.
Do not backdate a current map or relax the old interface's guard silently.

## Chosen implementation and alternatives

Reuse original find with narrowly audited source/map/detector/clock injection,
and call the existing real detector/pricer through an offline validating bridge.
Add opt-in closed-base-prefix evaluation at arbitrary microsecond-exact T to
period/frame/map builders. Price selection ends at the last complete base close;
publication, metadata eligibility, freshness and source session/shape gates use T.
No timestamps are rewritten. Existing strict defaults/results remain unchanged.

Calling the old newest-confirmation wrapper directly would omit valid source
choices. Moving T back to the last bar close would lose bars published between
close and T and change370-second freshness/session gates. Rewriting availability
to force a bar through would forge evidence. None of those paths is selected.

## Public boundary and remaining admission

Public inputs remain immutable typed bars/calendars/periods/corrections, never a
caller-computed ready map or source-choice boolean. Missing evidence is recorded,
not a losing trade. Original internal provenance gates and M5/M15 selection are
implemented; real external market-watch admission remains separate:

market_watch.py:1014-1112 calls find, then _score_entry, plan.tradeable, windows
outside_reason, floor.marketclock.entry_blocked, tracker.blocked_after_stop,
tracker.has_open and tracker.blocked_same_level. Only then is active_reversals
set, before episode deduplication. This distinction matters: a repeated episode
can still defeat an opposite producer without being sent again. Tracker record,
state persistence, notifications and broker integration follow; none is executed
by this research component. _producer_conflict:251 consumes active reversals.

The current implementation slice must not claim those outer gates, tracker
state, other producers, fills, labels, dataset/training readiness or full-goal
completion. Closed-base prefixes still do not reconstruct open-only ticks or a
partly observed base bar. Real broker calendars/basis/era and GC variant remain
evidence/human questions. Full B-I requirements remain open in the master tracker.
