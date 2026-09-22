# Source-faithful lifecycle gate, parking and retry

This is an additive recovery of a narrow chart-desk source component. It does
not introduce a trading rule and does not prove that a lifecycle message, price
move or journal record is a real economic trade outcome.

## Authority and component shape

Authority is chart-desk `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`,
`chartdesk/tracker.py` blob `b616b34022e436545d8c1daf85eced51614fd74e`.
Read/parse retained source only. `LifecycleGate(source)` owns one actual
`ClaimVerifier(source)` and one `OutboxJournal(source)`; its `threads` is the
journal's `LifecycleIdentity` object. Thus receipt cache scope follows the
actual simulated process and is not recreated per message/gate invocation.

The projected source order is `_persist_gated_lifecycle`, `gate`, `PARK`,
`PARK_MAX_AGE_S`, `_park_key`, `_park`, `_unpark_text`, `replay_parked`,
`_park_lost`, `_atomic_json`. Source functions become instance methods with
only `self` added. The constructor is the documented specialization; selected
source bodies, signatures, annotations, decorators and their relative order
must otherwise remain exact.

`PARK` is the logical key `chart-desk/out/parked_claims.json`, never an OS
path opened by the runtime. `PARK_MAX_AGE_S` is the exact source 3600.0.

## Gate and persistence behavior

`gate(msgs, state=None)` uses supplied state or exactly one `source.load()`.
It recovers matching through the accepted pure `_match_trade_for_text` and
group-receipt state through shared `threads._group_has`.

- Ambiguous messages bypass verification. A group ambiguity with no receipt
  for all matches becomes a personal send plus a blocked diagnostic; otherwise
  it preserves destination. Either way it exact-text unparks.
- Unmatched messages pass unchanged and exact-text unpark without verification.
- Identified lock/finish TP messages with targets call `verifier.target` for
  target zero. Other identified claims call `verifier.check_message`.
- Failed stale verdicts park and produce `STALE: {reason}`; failed
  contradictions only block. Neither is a send.
- A successful group update lacking its entry receipt is demoted personal and
  produces the receipt diagnostic; a normal success keeps destination. Both
  exact-text unpark.

`_persist_gated_lifecycle(msgs, state)` returns `[]` before any import/effect
when empty. Otherwise it calls `gate`; each send enqueues into the actual
journal with `threads.context(text, state)`. A blocked item whose text was sent,
or whose reason begins `STALE:`, has no journal diagnostic. Other blocked items
enqueue personal `blocked_lifecycle` then resolve that exact ID. The return is
the original `msgs`, not the admission result.

## Park and retry behavior

`_park_key` is `symbol|entry|first full stripped text line`. `_park` treats
absent/bad JSON as `{}`, preserves an existing key, otherwise records text,
one operation epoch, source symbol/entry and boolean `tr.get('to_group')` from
the matched trade (not the message-local destination flag), then writes full
JSON atomically. `_unpark_text` returns on absent/bad JSON, removes
all exact full-text records and writes only on a change.

`replay_parked(state=None)` reads no state/clock when artifact is absent, bad or
empty. Otherwise it takes one `now_epoch()` before iteration. Age expiration is
strictly greater than 3600; it emits a loss note. It finds only the first state
trade with equal symbol and entry difference below `1e-6`; no match is silently
dropped. The verifier sees a copied trade whose `claim_ts` is parked `ts`.
Success returns `(text, to_group)`, remembers the original birth time in the
actual journal, and logs release. Stale remains parked; contradiction logs and
creates loss note. The final keep image is atomically written even if empty.
The outer caller still must gate a released item; replay itself does not apply a
receipt check.

`_park_lost` computes the source Israel-clock display from parked timestamp or
a fresh operation epoch, sends the source courtesy personal `park_lost` note
through the journal, and catches only that enqueue error to stderr. The exact
Hebrew note is source behavior and must be retained in the AST projection.

## Raw source interface and effect boundary

The shared source implements all raw ports required by accepted verifier,
journal and identity contracts, plus `park_exists()`, `park_text(*, encoding)`,
`atomic_mkdir(path, *, parents, exist_ok)`, `atomic_mkstemp(path, *, suffix)`,
`atomic_fdopen(fd, mode, *, encoding)`, `atomic_fsync(handle)`,
`atomic_replace(tmp, path)`, `atomic_unlink(tmp)`, and `format_il_clock(epoch)`.
Atomic handles are supplied inert test/causal artifacts. The component retains
source call ordering and cleanup, but does not claim OS durability, fsync,
cross-process locking, Telegram delivery or exactly-once send.

No port may provide a final verifier result, match result, receipt decision,
parking result, queue row or atomic result. Ports expose raw bytes/handles,
clocks/state and offline effects only. There are no fallback filesystem,
network, broker or transport operations.

## Independent proof and limits

The auditor pins authority/blob, selected source symbols/order/signatures,
decorators/constants and exact substitutions, then compares the full projected
runtime AST. It invokes actual source audits for claim verifier, outbox journal
and lifecycle identity; any absent/error/blocked child blocks this audit. The
CLI requires an explicit retained source root, emits JSON and exits 0 only when
verified (2 otherwise). Readiness remains false.

This component is not full market-watch caller parity, replay certification,
historical data coverage, an economic simulator, a dataset, a trained model,
model promotion or authority for live notifications/trading.
