# Outer market-watch admission — source intake, not implementation

Date: 2026-09-09. Follows the approved existing-repository baseline. This records
read-only source findings for the next vertical-replay stage; none of these
additional gates is implemented by the reversal-producer component alone.

## Identity

Retained checkout parent:
`C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`.
Chart-desk commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`;
trading-floor commit `d827dd792cbd1d396b4ee325879c63e57388e07a`.
Source text was read, never imported or executed. Trading-floor HEAD and clean
status were checked; blob identities below were read using git rev-parse.

| Repository/path | Git blob |
| --- | --- |
| chart-desk/scripts/market_watch.py | f530fbe82cffbaf831c7a7725c7a9bf6143e6b8b |
| chart-desk/chartdesk/windows.py | 53453b73e7f0c48647945e7d58ba6b30ed8d4102 |
| chart-desk/chartdesk/tracker.py | b616b34022e436545d8c1daf85eced51614fd74e |
| chart-desk/chartdesk/entry_quality.py | 0cd76eb8c607690610f4559e5946a60e8f7647ac |
| chart-desk/chartdesk/zones.py | 92f7b99373b4f266a1d80e2d997b965f973d7698 |
| chart-desk/chartdesk/matrix.py | 28641487567c457b6922c2a63055659867bb4248 |
| trading-floor/floor/marketclock.py | 246b01255a2203e2a04c2ef7d549f67087b4f2c9 |

## Observed order and distinctions

`market_watch.py:1014-1112` consumes the reversal find result. Its sequence is
entry-quality annotation, source plan tradeability, hunting window, entry clock,
post-stop block, open-position slot, same-level block, active reversal registration,
episode deduplication and then publication/recording. See also the existing
REVERSAL-PRODUCER-SOURCE-CONTRACT.md. Do not turn the helper `conflicts` into
proof that this sequence ran.

- `_score_entry` at line89 attaches labels before operational gates and never
  branches on them. It reads recent aligned and opposing rejection evidence.
  `entry_quality.evaluate` is pure; its `shadow_block` describes a hypothetical
  stricter policy, not an approved veto. Promoting it would change the baseline.
- `windows.hunting`/`outside_reason` at lines138/144 use Asia/Jerusalem local
  hours: inclusive02:00, exclusive21:00. `rate` marks prime/normal/thin but does
  not itself veto. These are fixed source research rules, not fresh measurements
  of the new dataset and not exchange-calendar evidence.
- `floor.marketclock.entry_blocked:177` first blocks its explicit weekend window,
  then Friday times within90minutes of the source23:00 close. Source weekend is
  Friday23:00 through Monday01:00 local. This desk policy is not the instrument's
  historical session calendar. The module's crypto silence is a source policy,
  not a claim that crypto markets close then. In the actual reversal order the
  hunting gate can stop evaluation before the Friday preclose gate is reached.
- `tracker.has_open:1829` treats OPEN as exposure and explicitly does not count
  PENDING as an occupied slot. Unreadable/corrupt state fails closed. Direction
  None widens the check. Do not substitute the older `has_active` helper, which
  includes pending orders, for this actual caller's choice.
- `tracker.blocked_after_stop:3415` selects the latest STOPPED same-symbol/side
  row, uses real decision age, and releases after MAX_STOP_BLOCK_H=4.0 or one of
  its structural conditions. It sums matrix4h/1h net scores (not probabilities),
  tests the source +/-25bias release, then fetches15m/5-day history after stop
  for `_last_swing`, then `_cooldown_release`. The precise code's up/short and
  comparison conventions must be retained, not reconstructed from comments.
  Its outer exception path returns None, unlike has_open; a research adapter
  must expose missing/error evidence distinctly rather than certify admission
  from a quiet source failure or silently rewrite the source behavior.
- `_cooldown_release:3338` tests the new plan entry beyond the stopped stop by
  the resolved symbol pip; anchor changes/rejection are telemetry, not mandatory
  conditions. It may attach `plan.cooldown_release`. Its optional asof governs
  rejection telemetry; the enclosing function still uses wall clock/state/feed.
- `tracker.blocked_same_level:3519` checks same-symbol/side DONE or CANCELLED rows
  with a nonzero resolved_ts less than7200seconds old, and entry inside the old
  entry_zone, inclusive edges. STOPPED is handled separately. At the exact age
  boundary it does not block. The helper assumes already-causal state and does
  not exclude a future resolved_ts itself; an as-of state adapter must do so.
- `active_reversals[sym]` is assigned before checking the episode key. A duplicate
  episode can therefore remain active for opposite-producer arbitration even
  when no repeated alert is emitted. Notification and broker code must remain
  disconnected from offline reconstruction.

## Dependency work exposed by the intake

1. Explicit decision-time specializations of hunting/entry-clock rules; timezone
   data/version and DST tests. No use of these coarse desk windows as a substitute
   for the supplied historical price calendar.
2. Pure entry-quality parser/annotation, plus historical rejection evidence.
   `_recent_rejection:3267` reads a byte tail of EVENTS, filters kind/symbol/side,
   timestamps inclusive between since/asof and age <=1200seconds, then overlap
   or bounded distance. Replay must reconstruct the log prefix known at T;
   tailing today's final file can drop earlier evidence or admit later records.
3. Full matrix4h/1h calculations and source swing helper. `_last_swing:187`
   uses SWING_K=3 and both-side confirmation; the swing's center is not its
   information availability time. Matrix.net is weighted signed agreement.
   The full calculation closure still needs to be audited before adaptation.
4. Immutable as-of tracker state and episode-state evidence, with event-time,
   publication, ordering, error states and checkpoint/resume equivalence. A user
   supplied `blocked=False` is not proof of replaying these rules.
5. Reconstruct source advisory tracking separately from fixed-stop/full-TP1
   economic simulation. Their state transitions may differ; feeding economic
   exits into source alert gates without a named policy would change candidates.
   Portfolio filtering must later recompute policy-dependent slots/cooldowns.

These are implementation dependencies, not a request to invent new thresholds.
No real state/log files, raw data, accounts or live services were read. The
authoritative master still requires remaining producers, full feature coverage,
simulation, dataset and model validation; source intake does not close them.

## Follow-up source inspection: recording is another gate

Read-only follow-up2026-09-09 after the dependency component began. The exact
market-watch slice1060-1080 sets active_reversals before episode dedupe, renders,
then skips recording entirely without `--telegram`. Offline reconstruction must
name its selected source publication mode; it must never send Telegram merely
to obtain the record path. With publication enabled, record failure/false returns
prevent episode-state insertion. A pre-record gate pass alone is not acceptance.

`tracker.record:398` first checks nonzero entry/stop and computes `_higher_bias`,
`_thesis_baseline` and `_born_in_zone` outside its lock. `_record_locked:451`
rechecks has_open against current state, deduplicates complete geometry while
PENDING/OPEN, and archives an already-resolved same-geometry instance under a
send-time suffix before replacement. `_trade_identity:378` hashes canonical
symbol/direction/entry/stop/target prices/style, geometry rounded8decimals with
a16hex digest, and a state key whose entry display is rounded2decimals.
This is distinct from detector episode identity and individual send identity.

The initial row is PENDING unless `born` is true. `_born_in_zone:427` first
requires the build close inside the entry band, then uses source live-price
evidence: missing/stale quote defers to the build; available quote uses the
source one-sided reached test (short spot >= zone floor, long spot <= ceiling).
Exception returnsFalse. OPEN-at-send still records broker revalidation unverified;
it is not an economic fill. A synthetic replay needs explicit as-of quote
availability and exact source freshness, not an invented fill assumption.

Recorded fields include reasons, variant/group flag, style, immutable geometry,
obstacles, trade_id, kind, hit[], sendts, thesis_state/thesis_warned, optionally
bias_at_send and born-open timestamps. This is a source advisory state machine,
not the approved fixed-stop/full-TP1 economic ledger. Source calculations for
send-time bias/thesis and full subsequent resolver transitions remain to port.

`_recent_rejection` consumes `_tail(EVENTS)`, not a query of all historical
rejections. `_tail:3233` starts with400000bytes, drops a leading partial line,
expands x4 if needed up to an8000000 cap and can fall back to the entire file
for a pathological final line. Non-rejection lines affect which records survive
this byte window. Therefore an ordered list containing only semantic rejection
rows is insufficient to prove exact source-tail parity. The new causal memory
store preserves such rows but does not certify the original log's byte prefix.
Before binding the source selector, provide explicit historical full-log prefix
evidence or a separately named policy; do not silently replace source tailing
with all-history rejection lookup.

`symbols.resolve` is pure but broader than needed; its exact source map gives
pip0.01 for all three supported producer instruments. That is a source rule,
not an exchange tick-size claim and not permission to alias GC. If specialized
to these three inputs, its required branches/constants must be audited rather
than trusting a caller-supplied pip.

Follow-up symbol source blob: c2fd40c8a97d98aa3650d95c8fbe64a5ce43e8f7.
Chart-desk clean status/HEAD were rechecked during this intake.
`_higher_bias:2431` requires both4h/1h and returns their individual nets;
`_bias_against:2451` (fill/lifecycle policy) requires sum threshold plus no higher
frame still siding with the trade. Do not substitute it for blocked_after_stop,
whose inspected code uses the sum alone. These different callers are deliberate
source distinctions to preserve until a separately approved policy changes them.
`tradeplan.thesis_now:1721` reads4h/1h/30m/15m/5m; higher net averages two frames,
lower net averages30m/15m/5m, and5m bar_ts supplies confirmation identity.
`thesis_verdict:1749` uses signed lower net <=-WEAK_GATE(25) for broken and
>=THESIS_RECOVER(0) for held, with a deadband returningNone. The baseline defaults
to held on unreadable evidence; subsequent thesis-report handling is stateful
and has its own two-distinct-5m-bar confirmation, not an admission veto.
`_live_prices:2471` accepts finite positive price and age0..QUOTE_MAX_AGE_S420
inclusive; future quotes are not fresh. `tradeplan.born_in_zone:316` requires a
truthy build close inclusively inside entry_zone before the tracker quote test.

## Full-loop logging dependencies discovered before gate binding

Pinned source inspection2026-09-09: market_watch._log:61 adds sorted
sessions.current_session() if absent, then serializes {ts:time.time(), **row}
with ensure_ascii=False and default JSON separators plus a newline. The current
pass writes level_reversal_detected AFTER _score_entry but BEFORE post-stop.
Those bytes can change the rejection tail seen by _cooldown_release in the same
pass. Future reconstruction cannot freeze one tail for all calls or discard
non-rejection rows. Actual source newline/encoding must be explicit, not inherited
accidentally from the replay host OS. Other detectors log before reversal search.

Additional source blobs: chartdesk/slot_evidence.py
66c3f61b2c4a76ec4ded4b807843a4f042e2c5e2; decision_evidence.py
d20131bd87ed40703ba9194a3df55c7409d71cbb; sessions.py
2f44d322178feb14b0488abda51b40581db5b31f. Source HEAD reverified at the same pin.
decision_evidence.snapshot is pure geometry/context hashing: 8-decimal geometry,
24hex SHA256 of sorted compact ensure_ascii=False JSON with default=str.
slot_evidence.snapshot is read AFTER an occupied-slot gate and can describe both
PENDING and OPEN rows, even though actual has_open admits PENDING coexistence.
It records no_match_after_gate/unavailable separately and notes concurrent change;
it is not an additional veto. Future offline binding needs its own causal read.

market_watch._blocked adds these snapshots and tradeplan.reporting_waypoint,
then entry-quality shadow logging. reporting_waypoint:1102 only applies to the
source FAR_TP1_MARK refusal with obstacles and positive risk; chooses the farthest
obstacle by entry distance, with original tie order. It does not make that obstacle
a TP or a winning trade. _failed records detector_error into the same stream.

sessions.current_session:244 reads eight named source windows, using session_mask
and the window's own timezone/weekdays; start inclusive/end exclusive. These
labels are separate from Jerusalem hunting gates and from a historical exchange
calendar. Full source log parity needs this original session computation at T.
main:476 has a single-writer lock before loading episode state and computing
pass time; lock-contention exit differs for bar-close-trigger (75 vs0). A replay
must declare deterministic invocation order, not infer a live scheduler trace.

These are source findings, not implemented logging/binding. The active source
closure plan isolates tracker gates/recording only; complete loop/log/lifecycle
generation and other producers remain open in the full master plan.

## Full-watch state and producer ordering are not uniform

Further pinned source reads2026-09-09 establish these binding requirements:

- market_watch state is heterogeneous: TR/confluence/rejection/session-event
  cooldown keys hold scalar epoch numbers (for example508,542,717), while
  reversal/trend/tree/engine episode keys hold objects. _counter_htf_observe
  at157 can delete a key. Current MemoryEvent payloads are object-only and have
  no deletion operation; their tracker/episode evidence store is not a complete
  market-watch checkpoint. A full-watch state adapter must preserve scalar,
  object and deletion semantics explicitly, not wrap values without adapting
  the actual source consumers or silently discard nontrade state.
- Episode state is persisted once at905, before the later producer sections,
  and again at1599. Source crash/resume boundaries must not be collapsed into
  one alleged atomic source transaction. Tracker record has its own lock/save.
- Classic reversal and trend-reaction assign active arbitration before episode
  dedupe, but only record/update their episode after publication mode permits
  it and record returns true (1060-1077/1175-1192).
- Tree house/strict uses a6hour key at1300, updates st[key] BEFORE tree_trade
  logging and BEFORE its --telegram-gated record call at1348. The source log
  marks entry quality 'sent' before that recording gate. A tree_trade log or
  sent-quality annotation therefore does not itself prove successful recording.
  Even a false record can leave the in-memory tree cooldown updated for the
  final state write. Do not normalize this into reversal's different sequence.
- Engine dedupe at1460 tests direction/kind change, entry movement strictly
  greater than0.75ATR, or age>=6hours. It checks this before producer conflicts
  and clocks. Engine record at1514 is NOT guarded by --telegram: it precedes
  episode update, trade_plan log and group queue; only later private delivery
  is conditional. A single publication_enabled gate applied to all producer
  paths would change the original baseline.
- Brain logging at1377ff captures a full snapshot before _counter_htf_observe;
  it is explicitly observational, not another subscriber-trade producer.
  Its state/log effects still matter for complete raw-log replay and features.

Consequently the next full-loop adapter needs branch-specific caller projections,
full heterogeneous watch state and exact persistence/log ordering. Do not infer
the full machine from the accepted tracker methods or homogeneous episode rows.
These findings describe source behavior; no policy normalization or new domain
threshold was introduced, and no extra producer has yet been implemented.

Current adapter handoff constraint: pricing._source_plan serializes planned
geometry/reasons/warnings but not every Plan field (notably close/kind and the
subsequent dynamic annotations). It was designed as pricing evidence, not a
round-trip source Plan. Full outer binding must preserve the actual Plan from
the original producer through an internal typed evaluation path; do not rebuild
it from the reduced public pricing payload using guessed defaults. The existing
public report/hash interface should remain compatible and retain false readiness.

## Frame-provider binding: request depth is not delivered history

Read-only recheck2026-09-09 before causal matrix binding. matrix.read_tf:173
requests LOOKBACK[tf], renders Correction only when show is true, then computes
the same pure read_frame fields. read_symbol:188 is an ordered comprehension;
an exception aborts it rather than returning a partial dictionary. It has no
unverified/source-none veto. The separate producer's correction veto must not
be transplanted into this matrix path. LOOKBACK keys are4h240/1h240/30m90/
15m55/5m55; tracker post-stop separately requests15m5.

Important source detail: basis._fetch_corrected_raw:561's fresh TV path returns
the entire loaded nonempty df with source tv_daily at628, without trimming to
lookback_days or requiring that many days. The adjacent historical comment
mentions a splice, but the actual return does not call _splice_with_proxy.
MT5 at643ff also returns its loaded frame; the replay hook at748 calls serve(tf)
without lookback_days. Only the later generic data.fetch branch uses the request
parameter. Therefore240 requested days is not proof of240 delivered days, nor
authority to invent a universal minimum-day veto. Preserve request identity and
the supplied history_start/actual rows/calendar coverage separately. The finite
synthetic seed diagnostic proves calculations only, not historical feed retention
or a full-depth real-data study. Historical delivery/seed policy requires explicit
evidence before full-data parity; do not silently truncate or backfill a frame.

The next provider can reuse causal FrameSpec construction and correction
assessment, with a distinct request type for these six original key pairs.
MapFrameRequest's different allowed keys must not be bypassed or weakened. At T,
construct prices from closed base prefixes and retain actual publication cutoff;
evaluate source matrix with all resulting rows (including a target frame forming
from known closed base bars, as the existing source does). No extra closed-target
filter from the reversal detector belongs in matrix.read_tf. Any missing input
or calculation error must remain traced even when a surrounding tracker catch
returns no block or defaults a thesis to held.

## Storage binding must preserve source load/save and order

Further read-only source check before state/log provider work: tracker._load:221
returns an empty dictionary for a genuinely absent file, but propagates unreadable
JSON. Unknown historical coverage is not proof of an absent source file.
tracker._save:260 has behavior beyond atomic replacement: with allow_shrinkFalse
and an existing file it rereads current contents. Unreadable current state or
loss of more than len(cur)//2 keys when len(cur)>=4 causes a quarantine write
and RuntimeError before replacement. Creation forensics is best-effort and cannot
block save. The atomic write uses unsorted json.dumps(...ensure_asciiFalse,indent1).
Actual offline storage binding must preserve the refusal/re-read semantics and
model artifact effects explicitly, without accessing live files or inventing
an atomic whole-watch-pass transaction. Generic successful memory ports used in
current tests do not certify these source storage guards.

Tracker root key insertion order matters: same-level examines values in order
and returns its first matching row; stopped-row ties retain the first match.
Do not normalize an entire initial tracker dictionary with sorted keys and then
claim identical selection. Ordered payload text or ordered pairs can preserve
that identity. Existing event journals reconstruct root insertion order from
event sequence, but they are not full mutable watch-state stores with deletions.

market_watch._log:61 uses row.setdefault('sessions', sorted(current_session())).
Python evaluates that default even when sessions already exists: a future port
must preserve the session read and its exception boundary, not only the final
serialized value. The raw byte prefix must retain unsorted source row order,
JSON separators/encoding/newline profile and non-rejection events. These facts
constrain the next storage/logging work; they do not alter source policy or
claim that source writes, actual lifecycle or complete loop are implemented.

## Quote publication, log effects and resolver lock ordering (15:58 UTC)

Further pinned-source intake for the next causal quote/log/lock components:

- tracker.py:2471 _live_prices catches only file read/JSON load in the outer try.
  d.items() is outside it: a valid non-object JSON payload can raise, unlike
  an unreadable quote file, which yields{}. Per-row conversion errors are caught.
  Exact keys remain as supplied; no canonical alias is inserted by this reader.
  A known absent quote file is a FileNotFound read, NOT state._load's absent->{}.
  The quote provider must preserve this differing boundary and trace failures.
- scripts/tv_collect.py:447 _write_quotes merges into previous per-symbol content;
  quiet symbols remain. It serializes indent2/sort_keysTrue and atomically replaces
  after fsync. Quote freshness is NOT the whole-file modification timestamp.
  At555 the collector merges an event with wall-clock time; at558 it flushes on
  a monotonic interval (QUOTES_WRITE_INTERVAL_S=10). Observation and publication
  can differ; do not expose a queued event before the file write was available.
  This is one source writer; quote_pump is also named by source and must not be
  inferred fully mapped merely from this collector inspection.
- chartdesk/tv/identity.py:72/83 merge_quote/fresh_price_update makes that timing
  distinction explicit: valid lp updates ts AND price_ts; metadata-only updates
  update metadata_ts but must not rejuvenate price age. Source valid_price also
  excludes bool. Tracker's consumer is separately float-casting q.lp; do not
  confuse the producer's accepted events with the consumer's malformed-row rules.
- market_watch._log:61 mutates caller row via setdefault before mkdir/open/write.
  It eagerly calculates sessions even when supplied. Its {"ts":time.time(),**row}
  lets row.ts override the generated timestamp. Keep event payload time separate
  from append/publication time; no sorting/normalization of raw watch JSONL.
  Sessions at sessions.py:244 use session_mask/IANA local windows at the actual
  supplied clock. Existing map_sessions projection has SESSIONS/_hm but does
  not yet contain current_session/session_mask. Do not claim that dependency is
  already implemented just because session-level construction is accepted.
- market_watch.py:963 invokes closeout_check()+check() BEFORE new reversal
  candidates under _locked(wait=30,skip_if_busyTrue), then tracker.gate. A
  LockBusy skips those resolver calls, not the entire later producer loop.
  Generic _locked defaults are30s writers versus3s resolvers, but this caller
  explicitly overrides resolver wait to30. At tracker.py:128/148 busy markers
  persist continuous refusal; after120s a resolver may proceed unlocked. Normal
  writers also proceed unlocked on timeout, and nested process depth bypasses
  a second acquisition. Successful acquisition best-effort clears the marker.
  A trivial always-success lock is not evidence for these source paths.

The present storage binding models load/save and completed local effects only.
No claim is made that it implements these quote/log/lock/lifecycle dependencies.

## Lock policy versus operating-system timing (16:27 UTC)

Read complete pinned chartdesk/filelock.py and tracker._busy_for/_locked.
filelock.try_acquire creates a monotonic deadline, attempts immediately, then
polls every0.05s until success or a failed attempt at/after the deadline. Thus
the configured timeout is NOT evidence of actual elapsed time: success may be
immediate, retries can overshoot, and a successful post-deadline attempt wins.
Windows prepares a one-byte nontruncated region; POSIX uses flock. The offline
policy must not perform either OS action or pretend to certify them.

Source policy ordering: mkdir/open occurs before the outer try; acquire errors
still close an opened descriptor. Successful acquisition clears busy marker
best-effort. Busy read/float failures best-effort stamp current wall-clock time,
then return0. Negative ages remain negative; NaN fails the `<120` comparison and
therefore enters source fail-open. These are source behaviors, not recommendations.
Release errors propagate after depth decrement but descriptor close still runs.
Nested sections bypass mkdir/open/acquire entirely and unwind depth in finally.
The depth is process-shared, not thread-local; offline callers representing one
process must share one policy object, not create one per entry point.

Tracker record calculates bias/thesis/born before its lock; load and record.ts
occur inside. A future shared replay scheduler must expose post-acquisition time
and artifact publications to those latter reads. Simply adding the timeout to T
or freezing every port at pre-lock T would both invent behavior. Next source
policy projection will expose acquire/clock/artifact ports; it does not itself
supply a historical lock schedule, competing writers, or full-loop atomicity.

## Shared-clock binding must retain the pass anchor separately

Read-only next-binding intake after quote/watch acceptance and lock source port:

- market_watch.main:485 opens its own separate market_watch.lock, nonblocking.
  Failed acquisition returns75 for --bar-close-trigger, otherwise0, before watch
  state is loaded. This is NOT tracker.lock and must not share its reentrant depth.
- main:494 loads the complete watch state; at495 it reads `now` once. That pass
  anchor drives cooldown stamps, producer find(now=...), episode.ts and queue
  filenames. It is not refreshed after tracker resolver/record lock waits.
- _score_entry:98 reads its own current clock; _log:65 reads a current clock and
  independently computes sessions. Tracker.record reads bias/thesis/quote before
  its lock, then current state and record.ts inside. Thus neither one frozen T
  for all calls nor replacing all original uses of pass-now with operation-time
  is faithful once supplied operation times differ.
- level_reversal.find:269 accepts explicit detection now but calls levelmap.build
  and basis.fetch_corrected without passing it. Actual live dependencies can be
  read later. Current accepted as-of producer evaluates a coherent supplied T;
  it does not claim reconstruction of mixed-time live reads during long passes.
  Keep that interface unchanged; a full caller needs separate pass-anchor and
  operation/publication clocks, plus explicit source read evidence/scheduling.
- Watch state persists at905 BEFORE resolver/new producers and again at1599.
  Tracker state has separate guarded saves. No single transaction covers them.
- Reversal publication mode enables recording, but actual notification success
  is NOT a prerequisite: record succeeds first, then episode mutation, trade
  log, quality log, queue, health and private send. A send failure does not undo
  the tracker row or episode. MT5 branch remains disabled offline. Dry-run mode
  is not simulated merely by leaving source --telegram off, since that removes
  this producer's recording path. Model the source mode and transport effects
  explicitly without any network output.

Implications for the next scheduler/provider contract: keep pass_anchor, current
operation_time and stable same-time sequence; ports read at actual operation T;
preserve generated state/log effects and evidence across advances; never derive
elapsed time from a timeout. Distinguish explicitly declared deterministic
research scheduling from reconstruction of recorded operational timing. Neither
mode supplies missing historical quotes, prior watch state or external writes.
This is newly documented source evidence, not an implemented combined caller.

## Watch persistence and bar resolver: next source boundary (17:02 UTC)

Rechecked retained chart-desk HEAD68b1d091 and clean working tree; market_watch
blobf530fbe8/trackerblobb616b340 unchanged. Read main initialization494-496,
first persistence904-905, resolver block963-988, final persistence1599 and
complete tracker.check1113-1345/closeout_check3173-3224 directly from source.

Watch storage is NOT tracker._save: initialization is exactly json.loads of
STATE.read_text when exists, otherwise{}; both writes use json.dumps(st) defaults
and direct STATE.write_text. The first write has preceding parent.mkdir(exist_ok
True); the final one does not. There is no tracker shrink/quarantine/creation
guard, no sorting, no atomic replacement and no root-object validation in these
statements. Future binding must retain arbitrary parsed JSON and let original
consumers fail naturally, not silently normalize malformed content into{}. Keep
the caller's mutable st distinct from the last persisted complete image; unsaved
mutations/deletions must not appear in a restart image. Modeling completed local
writes cannot claim recovery from an actual partially written filesystem file.

The next bar lifecycle requires more than price touch: check fetches15m/3 (NOT
the accepted admission15m/5 request), skips unverified or tv_stale corrections,
uses index timestamp strictly greater than send ts, and continues without expiry
when that window has no rows. It calculates postfill extrema separately. Pending
expiry applies only when entry has not been touched; fills then recheck OPEN slot
and revalidate_pending. A fill's recorded time is the current source clock, not
automatically the first touched bar time. Already-open and newly-filled paths
share original protection/target ordering; desk_success movement annotations
are generated separately and may precede terminal handling in the same call.
When changed, _persist_gated_lifecycle runs before _save. This requires its own
gate/outbox/receipt/park dependencies; an in-memory sourceoutcome row alone is
not sufficient to reconstruct future state. These transitions remain advisory,
not the fixed-stop/full-TP1 economic simulation chosen for the first model.

closeout_check's comments describe weekend tracking removal, but its actual
body only reads stage/state/weekend_hold and formats notice messages; no mutation,
save or economic close occurs there. Follow executable behavior, not that prose.
The full caller concatenates these notices before check, then applies gate again
outside the resolver lock. Preserve both gate positions rather than assuming
one final gate is equivalent. No new lifecycle implementation is implied here.

## Lifecycle dependency detail and independent claim verification

Read actual position helpers548-686, outcome writer358-376, expiry/shelf/aged
revalidation1914-2027, complete still_valid2235-2428, gate/persist1421-1523,
complete desk_success.py and verify.py through independent fill locator180.
Additional pinned blobs: desk_success.py d2b2fdb2889841f587338e56041ffdc8df6c298c;
verify.py 3329fdb71f8aebdf13a6fa823e8be0d85e1ced03. Remaining verify methods and
other lifecycle dependencies are not claimed fully mapped by this intake.

- Resolver position_bars locates first entry-zone touch strictly after send if
  pending/no fill timestamp. Existing OPEN prefers bars whose stamps >= filled_ts;
  if none, it locates the containing earlier bar. include_fill_barTrue selects
  that containing bar even with later bars. _position_extremes lets the fill bar
  count adversely but never favourably. These exact distinctions must survive,
  not be replaced with all since-send highs/lows or an economic fill assumption.
- desk_success.observe_bars explicitly requests include_fill_barTrue, excludes
  the fill bar from paying bars and excludes the first original-stop bar and all
  later bars. Its observed_ts is the current detection clock, not the opening
  timestamp of the threshold bar. Proof binds version/trade_id/sendts/symbol/
  source/floor and resolved horizon. FLOOR XAU40/10=4priceunits, NAS70, BTC200
  is movement, never net economics. The source proof says caller certifies tape;
  the replay provider must supply that evidence and not infer certification from
  the method name. Classification/audited_classification is separate reporting.
- still_valid rechecks actual4h/1h bias versus send bias and stretch; age probes
  separately request15m/1h/4h with3days. Freshness uses each actual bar size scaled
  to15m-equivalents, hard>120 and soft>20; missing reads can reduce verification.
  Shadow EMA/session/stopdistance/structure4h400/vector15m60/news calls log without
  veto. Preserve their errors/IO effects; source missing is not a certified pass.
  revalidate_pending adds current tree agreement at age>=2h after core passes;
  _tree_agrees opposite direction blocks, unavailable defaults allowed/unverified.
- _outcome uses source directory/open/append ordering and JSON {ts:now,**row,
  event_ts:at}; row.ts can remain trade send time while event_ts marks write or
  an explicit repair time. Event time is not publication time. Outcome append
  occurs before final tracker save in check; later failure need not undo it.
  Expired ideas are shelved with original lineage, not merely removed.
- gate verifies text claims independently, with parked stale claims, receipt
  based group demotion and text-to-trade matching. _persist_gated_lifecycle calls
  that gate and enqueues/resolves outbox artifacts before save, but returns the
  ORIGINAL message list. The caller's second gate therefore is not redundant.
- verify._bars asks Binance venue FIRST, falling back to local corrected15m;
  it is not the resolver's already-fetched frame. The offline adapter must model
  these separate causal reads/results without network calls or invented venue
  equivalence. verify._fill_index has one-bar slack on send time, unlike resolver
  strict-after-send. Reusing resolver helpers would erase this deliberate
  independent check. A passing claim gate is still not an economic fill or label.

Next implementation sequence must cover source position helpers/movement proof,
remaining still-valid/tree/verify/outbox/receipt/park dependencies, then actual
bar/live/resolver caller lifecycle with its artifact effects. Pure helper or
source audit acceptance cannot stand in for that stateful sequence or other
producers. Current accepted admission requests must not be weakened to silently
stand in for these new source feed requests. Full master scope remains unchanged.

## Complete independent verifier intake (17:28 UTC)

Read complete pinned verify.py, including all functions through check_message;
this supersedes the earlier limited-through-fill-locator intake. Blob3329fdb7
and chart-desk commit68b1d091 remain the authority, not module prose alone.

- _binance_bars is a separate JSON transport and decoder: current UTC minus
  days, integer milliseconds,15m interval, limit1000, timeout15, OHLC floats,
  first timestamp field, no volume column. Its broad exception returnsNone.
  _bars asks it first for BINANCE, uses any nonNone result (even an emptyframe),
  then local fetch_corrected(symbol,15m,days) only whenNone. Local correction's
  unverified flag blocks; no new tv_stale veto exists here.
- target and stop use independent _fill_index, not lifecycle_bars. The source
  _frame INCLUDES the fill bar, including its favourable extreme in target.
  This differs from resolver paying-bar exclusion and is preserved behavior,
  not evidence that such an intrabar target was executable. Do not normalize
  these two readings just because module prose claims complete independence.
- target uses claim_ts else operationclock; stop prioritizes resolved_ts, then
  claim_ts, then operationclock. _frame caps opening timestamps <=claimclock.
  This alone cannot prevent final OHLC of a later-published containing bar
  leaking into an older claim; the eventual temporal provider must document
  actual observation/publication semantics, not certify from timestamp slicing.
- Missing/emptyframes produce failed verdicts. _covers unusually returnsTrue
  forNone/empty/badindex and allows900s; _closed_past needs next stampedbar,
  returningTrue on exceptions. They are internal predicates, not data approval.
  Missingfill target/stop use filled_ts with both predicates to distinguish
  stale from contradiction; fill also has a strict <45min currentclock grace.
- Source tolerance XAU0.5/NAS3/BTC15/fallback1 applies to target/stop comparisons,
  not entry-zone touch. _extreme guardsNaN but not arbitrary infinities; raw
  numeric exceptions remain source behavior and check_message catches them.
- check_message dispatches startswith emoji; target price uses original Hebrew
  regex, missingprice blocks; minimum-success head checks real identity proof;
  other messages pass as nofactualclaim. It never itself sends or saves a trade.
  The minimum route imports desk_success.reached despite broad prose saying
  no shared helpers; retain that explicit dependency, not an invented second
  movement proof. Source errors become failed Verdict with exceptiontypename.

Next complete source projection will retain independent functions and decoder
over explicit clock/frame/JSON-response ports, with no network transport. Tests
must exercise actual check_message routes, distinct tape, stale/contradiction,
fill slack, claim horizon, stopclock precedence and movement-proof identity.
Source port fixtures still do not establish real feed ownership or full gate/
park/receipt/outbox/caller execution; those remain separate required bindings.

## Revalidation closure detail beyond the verifier (17:32 UTC)

Read complete still_valid/_bias_against/revalidate_pending/_tree_agrees/_shelve,
complete stretch.py and emawin.read/_read_with_deep/read_stack; calendar_event_ts
and calendar_high_impact_in_window from tradeplan.py. New pinned chart-desk blobs:
stretch.py a74a591d9f3e014543e4023c694eab7eac845d43;
emawin.py e4ce74f49973ce7aeea8e33ec1c64ea86e8181e8;
rails.py 614920678bc58f1b920ebd145b1a4b0b5a159dff (only BUDGET_MIN read here).

Bias veto is not sign(sum) alone: _bias_against requires summed magnitude>=25
and every higher frame nonopposing the veto direction. It only cancels if the
stored send bias summed WITH the trade; neutral/missing/alreadyagainst send is
a distinct label. _higher_bias requires both4h/1h. These exact source rules
must not be inferred from simplified prose or silently adjusted for profitability.

still_valid's core returns before freshness/shadows on a real veto. Missing
stretch marks verifiedFalse and logs; a failed core records exception and keeps
going. Age reads independently request15m/1h/4h3days. Emptyframes are SKIPPED;
one available frame can therefore supply age_min even when another age request
was missing. An exception resets age_minNone. Corrections in those age probes
are not read. Do not claim the source guarantees every-frame coverage merely
because comments say "age every frame"; eventual causal traces must retain
all missing/caught evidence without transplanting a new source veto.

stretch.state is a full calculated dependency, not a supplied boolean. It asks
daily400, broker_shape_ok20, full tr_levels/weekly conversion; consumes verified
adr_from_open. Budget=(dayhigh-daylow)/ADR, anchored rails from dayOPEN. Extended
requires budget>=rails.BUDGET_MIN1.25 and beyond>0. It additionally calls15m20,
1h60,4h240 cloud deviations even though current still_valid veto does not read
them; those source reads/errors and state contents remain part of faithfulflow.
_atr is unseeded ewm, not a replaceable similarly named ATR utility. Missing
deviation deletes one context entry, not the whole stretch state.

Correction after tracing the actual dependency on2026-09-09: stretch's prose
and dataclass field comments describe open +/- ADR and ADR(20), but its state
calls tr_levels with defaults. Actual average_range(from_open=True) uses
open +/- ADR/2, and default adr_len=14 excludes the current daily row. The20
passed to broker_shape_ok is a feed-shape horizon, NOT the ADR averaging length.
Main synthetic real-range probe: prior H110/L90, current O100/H126/L100/C116
produces ADR20, rails110/90, used130%; exact source blobs verified. Preserve
executable behavior; do not translate misleading prose into a different formula.

emawin.read_stack shadow uses1h and15m, each defaultlookback2000. read also
optionally reads a separate deep archive; only pre-live rows can seed long EMAs,
overlapping live rows win, and close/ATR use the actual live series. Source
_read_with_deep requires2*n, continuous slope uses an ATR from the local span.
Existing simpler EMA observation adapter is not automatically this wholeconsumer.
Do not force deep GC archive into range/ADR data or claim that its seam is
historically certified. Additional feed/era/offset evidence remains required.

Calendar shadow parses real cached fields: nonzero numeric dateline
except bool, otherwise ISO date. Inside-window missingimpact raises; highprefix
returns the first input-order match. Offset-free ISO dates retain local-machine
timestamp interpretation in raw source, a portability issue for eventual
historical provider contract; no timezone should be silently guessed. Readonly
missing calendar is a shadow event, not noevent verification or a new veto.

These are dependency facts for subsequent source/provider plans, not newly
implemented vetoes or certifications. Current live broad regression runs on
unchanged runtime/tests while this documentation is updated.

## Complete EMA/deep reader boundary (20:45 UTC)

Main reread all emawin.py classes/functions (blob above)
and basis.MT5_SYMBOL_MAP; no source executed. read's fetch is outside the deep
try. lookback uses truthiness (`lookback or defaults`): daily2200, all other
frames2000 including unknown frames. No trimming of delivered rows. Source
correction flags do not veto this read; only corr.source annotates the result.

Deep filename uses the original symbol WITHOUT canonical_symbol: mapping
OANDA:XAUUSD=>XAUUSD, OANDA:NAS100USD=>NAS100, BINANCE:BTCUSDT=>BTCUSD,
TVC:VIX=>VIX,TVC:DXY=>DXY. Timeframe suffix map is4h:H4,1h:H1,15m:M15.
Unknown symbol generates a leading underscore and skips exists; known symbol
with unknown/5m/daily timeframe still probes e.g.deep/XAUUSD_.csv. Do not
silently suppress that source request or expand the symbol mapping.

Deep exists/read/CSV/time parse are inside one catch-toNone boundary. read_csv
then to_datetime(utc=True), set_index(time), sort_index are actual calculations;
returning a precomputed EmaState or deepFrame port would hide those semantics.
Offline logical-path and CSV-byte ports can preserve this without filesystem IO.
read_stack preserves inputorder and independently skips thrown reads; a repeated
timeframe is reread then overwrites its dict value, not a deduplicated request.

Each EMA independently uses live only unless len(live)<2*n. Only then may strict
pre-live deep rows be prepended. Duplication removal keep-last/sorting happens
only on that splice branch; do not globally normalize delivered live data.
Current close/window ATR come from live; slope numerator is3bars. Its denominator
uses _atr(src.tail(20)) when len(src)>20, which can include deep rows for short
live histories. It is not universally a live-only ATR. Missing convergence/NaN
EMA yields unconverged; source slope None/zero distinctions and EmaState's
strict-versus-loose trend/glued/cascade/window/weighted slope properties all stay.
Existing ema_snapshot uses fivebar delta and TR5/13/...; it is not this full
six-average (includes7) consumer and must remain unchanged.

## Full pending revalidation projection (21:07 UTC)

Reread complete tracker1982-2027,2215-2469 and tradeplan1667-1718. Concrete
source clarification: dateline accepts negative and nonfinite numeric values;
it is not restricted to positive epochs. bool/0 fall back to date. Impact.strip
is used only for emptiness validation; the highprefix test uses the unstripped
string. A leading-space High is therefore not High under the source rule.
Naive ISO dates inherit process timezone, still not a certified historicalfeed.

Missing/invalid pending send timestamp returns allowed/unverified after the
normal still_valid check; it does not cancel. Exactly2hours triggers current
tree check; opposingdirection wins over stopped_because; missing/stopped/errored
tree allows but prevents verified. _tree_agrees source docstring's nonveto prose
does not override revalidate_pending's explicit opposingdirection cancellation.

Complete new source contract REVALIDATION-SOURCE-CONTRACT.md and plan
2026-09-10-revalidation-source.md compose actual tracker higherbias, stretch,
EMA, structure, defaultPVSRA and source session calculations. _shadow is called
15times syntactically by still_valid; preserve each JSON/clock/effect boundary.
Full tree.walk is a separate explicit unbound dependency, not a fabricated
answer or certified existing adapter. Original fullwalk is ~700lines and reads
additional levelmap, brinks, checklists, wm, vectors and calendar dependencies;
sourceintake inspected its module interfaces, not its entire implementation.
Fullwalk and remaining producers stay mandatory in the master plan.
