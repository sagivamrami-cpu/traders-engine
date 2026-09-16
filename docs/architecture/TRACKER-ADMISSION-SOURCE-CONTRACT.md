# Original tracker admission and recording closure

Date:2026-09-09. Continuation of approved master C; not a new economic policy.
Prerequisite acceptance:125556Z-codex-admission-dependencies. Source intake:
MARKET-WATCH-ADMISSION-SOURCE-INTAKE.md. Entire master B-J remains binding.

## Purpose and boundary

Execute the actual tracker exposure, post-stop, same-level and record decisions
against explicit offline ports. This is the next source dependency for full
market-watch binding, not a replacement for that binding. Real causal frames,
bounded source memory and exact raw-log prefixes must eventually drive these
ports. No caller-supplied precomputed blocked/approved boolean is acceptable as
proof of the gates. Unit fixtures may supply controlled dependency readings.

Use a per-instance TrackerAdmission(source), never global monkeypatching or live
module imports. The source projection keeps original decisions/catches/ordering;
only I/O, time and references become explicit ports. Rewriting the gate from
comments would lose asymmetries; importing live tracker would expose side effects.
Cost: the adapted projection and dependency closure require independent auditing.

## Source authority

Chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9, trading-floor
d827dd792cbd1d396b4ee325879c63e57388e07a. Retained parent:
C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149.
tracker.py blob b616b34022e436545d8c1daf85eced51614fd74e;
symbols.py c2fd40c8a97d98aa3650d95c8fbe64a5ce43e8f7.
Read source as inert text. Confirm other used blobs with local git; pin them in
independent auditor authority and declarative manifest. Never execute source.

## Exact surfaces

Class TrackerAdmission(source), methods retaining original argument signatures
after self: has_open; blocked_after_stop; blocked_same_level; record;
_record_locked; _born_in_zone; _entry_band; _higher_bias; _thesis_baseline;
_live_prices; _recent_rejection; _cooldown_release. Pure _trade_identity and
_anchor_names may remain module functions. _tail_reader(open_reader, window=400000,
cap=8000000) replaces only path.open('rb') with open_reader(), keeping the original
seek/expand/line-drop algorithm and exception/None behavior. open_reader is a
factory for a fresh seekable binary context manager over the full causal prefix.
_tail_bytes(raw, window=400000, cap=8000000) is a small-fixture convenience wrapper
passing a BytesIO factory to _tail_reader. Never eagerly load the full log first.
thesis_now(symbol) becomes a class method using source.read_symbol;
thesis_verdict remains pure, with original WEAK_GATE25/THESIS_RECOVER0.
MAX_STOP_BLOCK_H4.0, LEVEL_COOLDOWN_S7200.0, QUOTE_MAX_AGE_S420.0 remain original.

Allowed offline substitutions, independently enumerated by the audit:
- _load() -> self.source.load(); _save(d) -> self.source.save(d).
- _locked() -> self.source.locked(); the with-block/recheck stays intact.
- time.time() -> self.source.now_epoch(); no default wall clock.
- matrix.read_symbol -> self.source.read_symbol; basis.fetch_corrected ->
  self.source.fetch_corrected. Preserve lazy order and original parameters.
- _tail(EVENTS) -> _tail_reader(self.source.event_log_reader). Pass the factory
  without calling it; opening failures stay inside the original tail catch.
- QUOTES.read_text()/json decode -> self.source.quote_payload() inside the
  original exception boundary; _live_prices still validates rows and freshness.
- Internal calls become self.method only for listed class methods.
- Imports of original pricing, basis, quality, swing and symbols become private
  audited offline modules, not dynamic sys.path/source-checkout imports.
- Pure source symbols module can be retained whole (stdlib only), to preserve
  original resolve(...).pip; it does not authorize any new public instrument.

Source port interface:
now_epoch()->float; load()->dict (detached source-advisory rows);
save(rows:dict)->None (offline transactional sink); locked()->context manager;
read_symbol(symbol,tfs:tuple)->dict of original TFView-compatible readings;
fetch_corrected(symbol,timeframe,lookback_days)->(DataFrame,Correction);
event_log_reader()->fresh seekable binary context manager (full historical log
prefix at call, read lazily; absent/unreadable raises on opening);
quote_payload()->dict (the source quote mapping, lp and ts per symbol).
Exceptions from ports must retain original catch/propagation behavior. The later
causal binding must additionally record every unavailable/error dependency so
a quiet source catch does not certify a complete historical decision.

## Observable invariants

OPEN occupies symbol/side, PENDING does not; corrupt exposure state fails closed.
Latest same-symbol/side STOPPED row controls post-stop. At age4h release before
any matrix/fetch. Otherwise actual order:4h/1h sum flip, 15m/5day post-stop swing,
entry beyond prior stop by source pip, then original block reason. The swing
requires strict source index>stopped_ts and at least8post-stop rows; use original
_last_swing(up=short), not a directional reinterpretation. Cooldown attachment
records anchor/rejection telemetry, neither a mandatory release condition.
Same-level applies DONE/CANCELLED, nonzero resolved_ts, age<7200 and inclusive
entry band; neither STOPPED nor PENDING is included. Preserve first matching row
and source malformed-row behavior; public binding must not supply future rows.

record must calculate higher bias/thesis/born before locked load. Recheck OPEN
inside lock; exact geometry dedup applies only PENDING/OPEN. Archive resolved
same-geometry rows with original timestamp suffix and preserve source behavior
on suffix collision (do not silently change identity). Geometry includes all
target prices/style/stop, round8/16hex identity, round2 display key. Retain every
stored field, born-open unverified broker evidence and optional bias_at_send.
Missing/failing save propagates; do not return a success after a failed write.
Advisory OPEN is never an economic fill; source tracker targets are not TP1 labels.

Build close must lie in original entry band for born-open; fresh source quote
uses one-sided reached condition, not inside-band. Missing/stale quote defers to
build. Future or nonfinite/negative quote is not fresh. Both bias frames or None;
thesis lower average uses30m/15m/5m, upper4h/1h; deadband or unread baseline held.

_recent_rejection must inspect original byte tail, preserve UTF8-ignore/malformed
JSON behavior, original substring prefilter, inclusive timestamps/max age,
overlap/distance, first row at equal timestamp, selected fields/rounding. Never
convert a semantic rejection list to alleged original bytes or sort by ts.

## Verification and next binding

Golden tests exercise real methods with in-memory ports and explicit traces:
gate order/early returns, boundary signs/ages/geometry, errors, record lock/recheck,
archive/save, quote freshness, exact byte-tail windows including huge last line,
competing/equal-time/malformed rejections. Verify no hidden filesystem/network/
wall-clock access in an isolated import-and-run process.
Audit full ordered projected AST, imports, constants, source identity and inherited
pricing/basis/quality/swing dependency bodies. Manifest narrowing, source/body/
threshold/alias/port-binding/order mutations must fail. Source CLI requires an
explicit root; tests accept TR_TREE_SOURCE_ROOT override and fail clearly if
required pinned checkouts are missing, never skip the audit.

Subsequent full market-watch binding must additionally reproduce source log
effects: _score_entry runs before level_reversal_detected logging, but post-stop
rejection telemetry reads after that append. Non-rejection bytes can change the
tail. _log also adds sessions and exact source JSON spacing/newlines. Other
producer logs, blocked/slot evidence and post-record logs must be included before
whole-loop raw-log replay is certified. Exact-source port tests are not that proof.
Outer active-before-episode, publication mode, producer ordering, causal evidence,
generated lifecycle and source/economic separation remain required. Public
replay/training/tradeable readiness remains false. No data download or live calls.
