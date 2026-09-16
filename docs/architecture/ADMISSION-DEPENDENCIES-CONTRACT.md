# Admission calculations and causal memory contract

Date: 2026-09-09. Engineering continuation of the approved master design and
MARKET-WATCH-ADMISSION-SOURCE-INTAKE.md, not a new trading policy.

## Place in the complete path

The internal reversal producer is accepted. Before its result can become an
admitted alert, the historical path needs original clocks, entry-quality
annotations, post-stop matrix/swing calculations, tracker state, rejection
history and episode deduplication. This component supplies independently
testable calculations and causal memory evidence. It does NOT complete the
outer gate orchestrator, reconstruct tracker lifecycle transitions from prices,
or emit labels. Those remain mandatory in master area C/E/F.

Use isolated pure source projections plus a typed causal state store. Importing
the live desks would expose filesystem, wall-clock and notification effects;
rewriting formulas from descriptions would risk changing the approved baseline.
The source projection approach follows the already accepted adapters. Its cost
is explicit dependency/audit maintenance; source parity is not predictive edge.

## Source calculations

Pin chart-desk to 68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9 and trading-floor to
d827dd792cbd1d396b4ee325879c63e57388e07a. Preserve ordered AST definitions and
transitive dependencies for these surfaces:

- matrix ToolRead, TFView, WEIGHTS, LOOKBACK, four read functions, _atr, _clip,
  TOOLS, _bar_ts. Add read_frame(df, tf, basis_note=None), the pure calculation
  portion of read_tf, without fetch. Keep TR's unseeded ATR distinct from
  indicators' seeded RMA used by SuperTrend. Preserve VWAP UTC-day anchoring,
  zero-volume fallback and even source NaN behavior; document, do not sanitize
  it into a new score. These scores are descriptive, not win probabilities.
- toolkit supertrend_ladder, ladder_state, vwap_bands and their complete pure
  indicators dependency closure. No unrelated LuxAlgo reversal code.
- Full pure entry_quality parser/evaluate closure. shadow_block is annotation,
  never permission to veto. Rejection selection/log replay is not implemented
  by evaluate itself.
- windows hunting/outside_reason and required constants; marketclock entry_blocked,
  is_closed, minutes_to_close, now_il and their constants. Offline clock entry
  points require an explicit aware datetime, never default to wall time. Preserve
  Asia/Jerusalem rules/DST and exact source reason strings. These desk rules are
  not a historical exchange calendar.
- zones._last_swing with SWING_K=3, exact right-side confirmation and comparisons.

Vendor code remains private. Source audit checks pinned repo identity, exact
blob hashes, original and adapted ordered AST projection, allowed imports,
dependency closure and deliberate clock/read_frame specializations. Mutations
of source constants, bodies, order, dependency aliases or vendor definitions
must fail. No import/exec of the retained live source checkout. Reuse existing
vendor dependencies only when audited against the exact required source bodies.

## Causal memory

New state.py provides immutable MemoryEvent and MemoryJournal types and
memory_asof(journal, decision_time). Events are supplied evidence, not proof that
the source tracker generated a state transition. The journal declares origin
and completeness as of a supplied start timestamp. No implicit empty state.

MemoryEvent fields: event_id, sequence (native nonnegative int), stream
('tracker', 'episode', 'rejection'), key, observed_at, available_at, payload_json.
An event is a full row replacement in tracker/episode streams; rejection is an
append-only log entry keyed by event_id. JSON must be canonicalizable, a mapping,
finite, with string keys and no duplicate JSON keys. Frozen records hold text,
not caller-owned dictionaries. All event/key/journal identities must be UTF-8
encodable at ingestion; valid non-ASCII text is preserved. observed_at <=
available_at; timestamps must be aware and microsecond exact. Events must have
unique IDs and sequences globally. Journal
events are an immutable tuple in strictly increasing sequence order; available_at
must be nondecreasing, matching the recorded append order. Equal-time events use
sequence. No sorting silently repairs corrupt ingestion.

MemoryJournal fields: journal_id, origin ('supplied_source_advisory'), start_at,
covered_through, complete (exact bool), events. start_at is an explicit attestation of complete
initial history; it does not certify the source or create historical evidence.
Events cannot precede start_at or be published after covered_through. The empty tuple plus complete=True explicitly
asserts a clean state over that interval; complete=False is unavailable, not empty.
T outside [start_at, covered_through] is unavailable. Extending coverage without
changing visible events leaves an earlier available snapshot/hash unchanged.

At T select only events available_at <= T (and observed_at <= T). Reduce by
sequence. A later revision never rewrites an earlier snapshot. For tracker rows,
numeric top-level ts/resolved_ts and for episode/rejection ts cannot lie after
event.observed_at; invalid types/nonfinite values are rejected. A malformed source
row otherwise stays visible to the source gate (e.g. missing state), rather than
being discarded as if it did not occupy exposure. Deletion is not supported.
Epoch comparison is independent of ambient Decimal precision. Numeric ts/resolved_ts
that lose their decimal value under canonical JSON float serialization are
explicitly rejected at ingestion; accepted journals must remain restorable.

Output is a detached JSON-safe report with schema causal-admission-memory-v1,
status AVAILABLE or UNAVAILABLE, decision_time, journal identity/origin,
tracker_state, episode_state, rejection_events, selected event IDs and content
evaluation_hash. Unavailable reports carry no usable state. All readiness flags
remain false. Future-only events are excluded from the evaluation hash, so
appending future events cannot change an earlier feature snapshot. The full
journal checkpoint separately includes all supplied events and a checksum.

checkpoint_memory(journal) -> dict and restore_memory(checkpoint) -> MemoryJournal
must validate full structure/checksum/version and preserve exact timestamps,
sequence, payload and origin. Split/resume equivalence is an evidence-store
property only; it is not yet whole-engine replay checkpoint certification.

## Verification and boundaries

Source projections: golden synthetic calculations, native source behavior edge
cases, clocks at exact boundaries/DST, annotations, swing confirmation and
mutation-resistant parity tests. Causal memory: delayed publication, future
revision invariance, same-time ordering, corruption, detached outputs, JSON
round-trip/checkpoint tampering, incomplete versus explicit empty state.

No live state files, feeds, notification calls, broker operations, real market
labels, source instrument aliases or existing live modules are changed.
The real-data GC/OANDA question stays open. Source advisory memory must never be
silently replaced by fixed-stop/full-TP1 economic position state.
