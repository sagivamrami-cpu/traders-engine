# Causal quote and watch-log IO contract

Approved master C continuation, not a new trading rule or permission. Source:
chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9; sessions.py blob
2f44d322178feb14b0488abda51b40581db5b31f; scripts/market_watch.py blob
f530fbe82cffbaf831c7a7725c7a9bf6143e6b8b. Existing tracker _live_prices/_tail/
_recent_rejection remain the consumers; no rewritten quote-age or rejection rule.

## Inputs

ArtifactSeed is frozen/keyword-only: seed_id,source,kind,status,observed_at,
available_at,covered_through,content. Exact trimmed UTF-8 identities; kind exactly
quotes/watch_log; status PRESENT/ABSENT/UNREADABLE/UNKNOWN. PRESENT quotes content
is exact UTF-8 text, including invalid JSON; PRESENT watch_log content is exact
bytes, including invalid UTF-8 or torn final line. Non-PRESENT requiresNone.
Aware microsecond-exact UTC times, observed<=available<=covered. Coverage attests
no unrepresented external changes through covered_through. It does not prove the
feed/history, inspect payload timestamps or invent omitted external publications.

CausalQuoteReader(*,seed,decision_time) validates exact seed and kind; quote_payload()
returns fresh json.loads of original text at T. Missing file raises FileNotFound;
UNREADABLE raisesOSError; UNKNOWN/unpublished/expired raises InputUnavailable.
No empty-dict substitution, alias, lp/ts normalization or replacement with candle
close. now_epoch() exposes this context's explicit T for original tracker reads.
Trace retains failed reads/JSON parse. Valid nonobject JSON stays nonobject;
consumer d.items errors retain the source boundary. Row freshness remains original
420s inclusive, including future rejection and its original malformed-row catches.
Metadata/file publication is distinct from the last-price ts inside the payload.

## Source logger and raw prefix

Private WatchLogger(source).log(row) is complete original _log with explicit ports:
current_session(), ensure_out(), event_log_writer(), now_epoch(). Preserve eager
session calculation/setdefault mutation before directory/open; caller sessions
are not overwritten; row.ts overrides generated ts; clock call still happens.
JSON is unsorted/default separators/ensure_asciiFalse plus newline. No extra
payload filtering or timestamp rewrite. Open append creates an empty file even
if later serialization fails. Failed write cannot invent a completed append.

Private watch_sessions has source session_mask and required-clock current_session_at
(*,decision_time,**kw); only optional wall-clock expression/signature replaced.
Reuse original SessionSpec/SESSIONS/_hm from map_sessions. Audit that inherited
module against its original complete four-symbol projection too. No weekend or
new session policy. TZ database version is environmental lineage for later replay.

CausalWatchLog(*,seed,decision_time,newline) accepts only watch_log seed, explicit
LF/CRLF. log(row) drives actual WatchLogger; event_log_reader() opens the current
complete byte prefix for original _tail_reader. No semantic rejection-only cache,
reserialization, repaired torn lines, added newline before append or sorted keys.
Non-rejection bytes participate in source tail windows and widening. Original
reader may returnNone on source read failure; port trace must remain available.

Append-only chunks plus a seekable prefix reader avoid joining/copying the entire
log at each open/read. Reader captures byte length at open; later appends are not
visible through that reader. It supports seek/tell/read/context close; read only
materializes requested bytes. An actual source fallback read-all may still do so.
No OS files, file-descriptor races, partial OS writes, competing appenders or I/O
latency are simulated. Unknown/unreadable prefix cannot be appended faithfully:
block open/write after source session mutation, do not pretend old bytes were empty.

advance_to(T) moves the log context monotonically within published/covered input;
it retains chunks/effects without a per-decision full-prefix copy. Existing readers
retain their captured prefix. Backward/naive/submicrosecond/out-of-coverage advances
raise without changing the clock. snapshot() explicitly materializes one full
ArtifactSeed at currentT, samecoverage/source/id; not a full-loop checkpoint.
Successful generated appends are observed/published at their operation T, independent
of possibly overridden/backdated row.ts. Detached trace records attempts and
failures with operation time. Snapshot export is the only eager whole-prefix copy.

## Tests, evidence and remaining scope

RED before runtime. Test quote shape/errors/detachment, price freshness versus
metadata, delayed publication, missing/future coverage and actual born OPEN/PENDING
via original tracker. Test original log byte literals in both newline profiles,
row mutation before failure, eager session read, caller ts/sessions, malformed
serialization and absent-file creation. Real source sessions at summer/winter,
weekend and DST-transition dates. Seed/chunk boundaries, immutable reader cutoff,
seek tail/widening and actual _recent_rejection before/after same-pass append.
Earlier readers/payloads must not see later mutation; failures survive source catches.
Audit pins repo/baseline/blobs and full private logger/session/dependency projections;
mutation tests reject changed order/clock/JSON/session constants/extra imports.

Neither reader nor logger claims full provider/market-watch replay. State/frames
already exist separately; original locks/caller sequence/watch state/lifecycle,
other producers and economic simulator/dataset/models remain. No live outputs.
