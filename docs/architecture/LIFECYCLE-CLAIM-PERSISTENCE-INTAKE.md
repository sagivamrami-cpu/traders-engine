# Lifecycle claim gate and persistence — source intake

2026-09-10. Read-only next dependency intake; not implementation or acceptance.
Extends MARKET-WATCH-ADMISSION-SOURCE-INTAKE.md after actual tree/revalidation
binding. The full master C/D and E-I requirements remain unchanged.

## Source authority and inspected scope

Retained checkout parent:
`C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`.
Chart-desk HEAD checked at68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9.

| File | Blob | Read scope |
| --- | --- | --- |
| chartdesk/tracker.py | b616b34022e436545d8c1daf85eced51614fd74e | _fmt; full text matching, gate, persist, park/replay/lost/atomic writer, receipt migration and _group_has |
| chartdesk/trade_threads.py | b05cfcf45cb420c40254154e80d3792a7b1685b9 | whole module |
| chartdesk/outbox.py | 1cf608f81e30c82ddd83b211a0ca743133699e45 | module setup, journal/append lock, merge, remember_born, enqueue/mark/pending, resolve/resolve_text; delivery implementation inspected but not certified |

Original modules were read as text, never imported or executed. No real queue,
receipt, parked-claim or account artifacts were read. The accepted
`_vendor/claim_verifier.py` already supplies actual ClaimVerifier(source).
It does not implement this outer gate or its persistence dependencies.

## Text matching and thread identity are different consumers

Tracker._fmt strips only the symbol prefix before colon. _side_from_text checks
literal spaceSELL before spaceBUY. _prices_in_text requires a decimal point;
it accepts commas and uses the original regex, not an inferred trade parser.
_text_has_price tolerance defaults0.02. _match_trade_for_text compares symbol
text and optional side, then entry matches, stop matches, then fallback states.
Multiple entry matches are disambiguated by a named stop/target in the text;
otherwise ambiguity survives. Fallback excludes CANCELLED and prioritizes OPEN,
then PENDING, then remaining states; a pool must have exactly one member.

trade_threads.HEAD is a separate anchored lifecycle-marker/symbol/BUY-SELL/price
regex. identity strips an initial late-delivery line before matching. context
reads tracker state only when no state is supplied; then uses tracker matching
and requires entry agreement with the regex within0.011 (strictly greater fails).
It snapshots symbol/direction/entry/stop/targets/style/trade_id/ts and adds its
own current event_ts. These two price tolerances must not be collapsed.

## Gate behavior that affects reconstruction

gate loads state once only when not supplied, preserving insertion order.
Ambiguous messages bypass factual verification. For a group-bound ambiguous
message, no receipt among the matches demotes to personal and also records a
blocked diagnostic; otherwise it retains destination. It un-parks that text.
Unmatched messages also pass and un-park, without calling the verifier.

Identified lock/finish messages containing TP with nonempty targets verify the
first target directly. All other identified messages call actual check_message.
A failed stale verdict parks the claim and emits a STALE-prefixed blocked
reason. A contradictory failed verdict blocks without parking. Successful
claims with no group receipt are demoted, not silenced; the same text appears
in send and blocked with a receipt diagnostic. Successful claims un-park.
Neither message admission nor a verified price claim is an economic fill.

_persist_gated_lifecycle returns[] immediately for no messages. Otherwise it
runs gate, computes accepted-text set, then enqueues each send with the actual
trade_threads.context(text,state). Blocked texts already in that set and stale
blocks are skipped. Other blocks enqueue a personal blocked_lifecycle entry
then resolve its event ID. It returns the ORIGINAL msgs list, not gated send.
The market-watch caller's later gate therefore remains necessary.

## Receipt evidence and process cache

_group_has stats the receipt file on every call. OSError returnsFalse. It only
rereads when st_mtime_ns differs from process cache mtime, initially0. Cached
keys and mtime update after successful processing; no fresh clock is consulted.
An unchanged mtime can intentionally retain prior parsed receipts; cache must
be per simulated process, not reset per gate call or shared across experiments.

Blank/torn JSON lines are skipped; malformed parsed rows are not universally
caught (outer read catches only OSError). Legacy missing-style receipts try
the named .json queue file, preferring out/group_queue/done over the queue root.
Missing/bad JSON returns no migration. The file's own geometry is hashed for
scalp/intraday/swing using actual _trade_identity; defaulting all to intraday
would wrongly reject a delivered swing. Final keys carry canonical symbol,
side, entry rounded2, lowercase style, geometry ID and delivery timestamp.
Unparseable delivery timestamp becomes0. A missing trade geometry ID is
calculated from its own stop/targets/style. Receipt qualifies only on all key
fields and delivery timestamp >= send_ts-120. No upper time bound exists in
this source consumer: eventual causal provider must prevent future receipts.

## Parking preserves first claim and has separate effects

_park_key combines symbol,entry and full first text line, not just marker.
_park absent/bad-read JSON starts{}; existing key is not overwritten, retaining
the first text/time. New record uses an operation clock and original trade
to_group. _unpark_text removes exact full-text matches; unchanged sets are not
written. _atomic_json is a separate durable operation, not tracker._save.
It creates parent, serializes unsorted ensure_asciiFalse JSON, fsyncs temporary
file, then replaces. Offline effect ports must not claim actual OS durability.

replay_parked does not read tracker state when the park artifact is absent,
unreadable or empty. Otherwise it reads one current now before iteration.
Expiry is strictly >3600seconds. Matching uses first symbol/entry match within
1e-6, not gate's side/style/geometry selector. Missing trades drop silently.
Actual verifier sees a copied trade with original claim_ts. Success returns
the parked destination, calls outbox.remember_born with original claim time,
and logs release. Stale stays parked; contradiction and expiry generate a
personal park_lost notice. Final keep image is saved after iteration. No receipt
gate occurs inside replay_parked itself; the outer caller must still apply it.
_park_lost uses original Israel-clock formatting and queues a courtesy message;
its queue errors are caught and printed. Preserve that distinct error boundary.

## Outbox journal semantics required before lifecycle save

_rows returns[] on proven absent journal; it skips blank and JSON-error lines.
Read errors and structurally malformed parsed rows can still propagate. _merge
preserves first ts while later rows update other fields and last_ts. It does not
turn delivery history into trade outcome history.

enqueue rejects nonstring/blank payloads before its clock. It computes thread
identity/context before popping process-local _BORN and before append lock.
Event ID is SHA256 of integer minute|text, first16hex. Read/decide/write happens
under a SEPARATE blocking append lock (not tracker lock or flusher lock), and
_write must not acquire it again. Actual lock's acquire receives timeoutNone.

Same-ID DELIVERED/RESOLVED is never resurrected. Same-ID PENDING retains attempts
and may only upgrade group destination. Cross-minute PENDING with exact text
and age<=600seconds deduplicates similarly, using original iteration order.
New row starts PENDING/attempts0/sent_personalFalse/sent_groupFalse. Group thread
identity adds reply_required/context. A truthy older remembered birth adds born;
zero birth does not. _mark reads a separate clock, appends under lock. resolve
is an explicit RESOLVED mark; it is not a trade exit or a Telegram delivery.

The retained outbox includes live-store test protections. Offline projection
must make raw effect sinks explicit and unreachable by default; do not point
STORE to the real checkout or import source to reuse these functions. Full
flush/send/delivery-health behavior remains later caller/transport work; no
real notification or broker operation is authorized by this research task.

## Next implementation requirements

Build the actual matching/receipt/thread consumer and process cache, then
actual gate/park/retry and enqueue/resolve persistence around the existing
ClaimVerifier, using explicit raw artifact/clock/lock/write ports. No supplied
final receipt/verifier verdict or final queue state as proof of computation.
Independently audit pinned source projections and actual inherited verifier/
identity dependencies. Verify real synthetic tapes cause pass, contradiction,
stale park/retry, demotion, duplicate suppression and ordered effects.

After this closure, bind original bar/live resolver and market-watch ordering
to causal frame/artifact providers. Current CausalAdmissionContext only advances
supplied tracker lock steps and has a restricted admission frame request set;
it is not a complete provider for tree/deep/options/calendar/receipt/outbox.
Do not weaken its accepted public contract or silently infer all operations
are instantaneous. Full causal scheduling, checkpoint/process-state semantics,
other producers and economics/dataset/model work remain required.
