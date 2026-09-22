# Causal quote and watch-log ports

`trading_system.tree_replay.admission_io` supplies `ArtifactSeed`,
`CausalQuoteReader` and `CausalWatchLog`. They use in-memory supplied evidence,
not live quote files, notifications or broker data. No source threshold changed.

## Evidence and quote reads

ArtifactSeed has seed_id/source, kind (quotes/watch_log), status, observed_at,
available_at, covered_through and content. All clocks must be aware/microsecond-
exact; observed<=available<=covered. Coverage is an explicit attestation of no
unrepresented external updates through its end, not automatic historical proof.

PRESENT quotes require original UTF-8 text; PRESENT watch_log requires exact bytes.
ABSENT, UNREADABLE and UNKNOWN requireNone and mean different things. Invalid
JSON may be faithfully supplied as text; invalid UTF-8/torn lines remain raw log
bytes. Neither is silently repaired. Quote payload timestamps are not rewritten.

```python
quotes = CausalQuoteReader(seed=quote_seed, decision_time=T)
payload = quotes.quote_payload()
```

Each quote read reparses the original text, so returned mutations do not leak.
Absent/unreadable files raise, unknown/unpublished/expired evidence raises
InputUnavailable. Read/JSON failures stay in trace even if original tracker
returns no prices. Valid nonobject JSON stays nonobject: the original consumer's
d.items error is not transformed into a provider empty-dict fallback. Original
tracker still owns price/age conversion,420s inclusive freshness and born state.
Metadata-only updates and file publication cannot rejuvenate an old payload ts;
bare symbols are not aliased and candles do not substitute for supplied quotes.

## Original logging and byte prefixes

```python
log = CausalWatchLog(seed=watch_seed, decision_time=T, newline="LF")
log.log({"symbol": symbol, "kind": "rejection", "direction": direction})
with log.event_log_reader() as reader:
    reader.seek(0, 2)
    size_at_open = reader.tell()
log.advance_to(next_T)
```

newline must explicitly be LF or CRLF; no platform default is assumed. The
source logger calculates original current sessions at the context clock, mutates
row.setdefault before mkdir/open, and serializes unsorted/default-separator
JSON with ensure_asciiFalse. Existing sessions are retained, but calculation is
eager even when supplied. An existing row.ts overrides generated ts; its clock
call still occurs. Payload time and actual append/publication time differ.

Append opening creates an empty PRESENT file from known ABSENT before JSON
serialization. A later serialization failure leaves that empty file and caller
session mutation, with a failed log trace. Encoding failure never appends invented
bytes. Unknown/unreadable prefix blocks faithful append after the independent
session step. This is missing historical evidence, not proof an original live
writer would have failed. Real OS permissions/partial writes are not simulated.

Every original byte is retained, including non-rejection events and malformed
lines. Appending does not insert a separator before a torn final line. Original
tracker _tail_reader remains responsible for windows, line-boundary widening and
fallback read-all. The provider never substitutes a semantic rejection-only view.

The log is held in append-only chunks with cumulative byte ends. Each reader
captures the current length and reads requested spans by seek/bisection. Opening
or taking a short tail does not concatenate the whole prefix. Old readers never
see later appends, including after advance_to. This models ordered single-writer
replay snapshots, not concurrent OS file-descriptor behavior. Source read-all
fallback still materializes its requested bytes; memory use includes all retained
chunks. This component is not a disk-backed ten-year archive or retention approval.

advance_to is monotonic and requires covered/publication-valid time. Invalid
advances do not change the clock. It retains chunks without full-prefix copies.
snapshot explicitly materializes a complete watch ArtifactSeed at currentT with
the same source/id/coverage. Snapshot is one artifact handoff, not a full replay
checkpoint; effects, input cursors, state/locks/lifecycle need whole-loop ownership.
Trace is a detached ordered list of operation times, statuses and failure reasons.
Do not mutate backend internals or use a later prefix as an earlier source seed.

## Verification and scope

Private watch logger/current-session/mask projections and the inherited
map_sessions table/helper module are audited against pinned repo/commit/blobs.
The logger's exact port substitutions and clock signature adaptation are checked
as whole modules, including imports. The audit never executes retained source.
The existing tracker audit separately covers quote/rejection consumers. Source
timezone behavior depends on the environment's IANA database; full replay must
record that dependency and certify its actual historical feed/publication inputs.

```text
python -m pytest tests/tree_replay/test_admission_io.py tests/tree_spec/test_watch_io_source.py tests/tree_replay/test_tracker_admission.py tests/tree_replay/test_tracker_storage.py tests/tree_replay/test_admission_frames.py -q --tb=short
python tools/check_watch_io_source_parity.py --source-root <retained-source-parent>
python tools/check_tracker_admission_source_parity.py --source-root <retained-source-parent>
```

Tests use TR_TREE_SOURCE_ROOT to override the retained parent, never silently
skip a missing audit. They exercise real original quote/born/rejection consumers,
source log bytes and sessions, publication/coverage, partial creation failures,
reader cutoffs, chunk boundaries, source tail widening and same-time rejection ties.
Fault injection is scoped to independent failures, not supplied net/born decisions.

State and frames remain separate accepted components. Original locks, main caller
order, heterogeneous watch state, generated lifecycle, all producers, economic
simulation, dataset/models and full shadow gates are still required. No full
replay/readiness claim, real-data acquisition, notifications, deployment or trading.
