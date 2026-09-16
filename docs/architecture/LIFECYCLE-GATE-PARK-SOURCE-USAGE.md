# Offline lifecycle gate, parked claims and retry

Status: accepted after independent task/audit/final reviews. This component is
neither a delivery service nor an economic trade outcome.

```python
from trading_system.tree_replay._vendor.lifecycle_gate import LifecycleGate

gate = LifecycleGate(raw_source)  # one source-process instance
returned_original_messages = gate._persist_gated_lifecycle(messages, state)
released = gate.replay_parked(state)
```

`gate` matches a lifecycle message through the accepted source matcher. An
unknown message passes untouched. An ambiguity never asks the price verifier;
it uses actual cached delivery receipts and demotes a group message only if none
of its possible trades has a receipt. An identified claim uses the independent
claim verifier: stale means park/retry, while contradiction means block.
Success without an entry receipt is demoted to personal delivery with a
diagnostic. No branch is a fill, a broker effect or a successful trade result.

`_persist_gated_lifecycle` returns the original caller list. It persists sends
through `OutboxJournal`, using the actual shared thread context. It does not
persist stale diagnostics or a diagnostic whose text has already been sent.
Non-stale blocks are journaled as `blocked_lifecycle` and immediately resolved;
that records an operator event, not a delivery or trade exit.

Parking uses logical `chart-desk/out/parked_claims.json`. The key is source
symbol, entry and full first claim line. First claim wins; exact full text is
required to unpark. The stored destination is the matched trade's source
`to_group` field, not the message-local destination flag; this surprising
behavior is retained deliberately for source fidelity. Retrying reads
state/clock only after nonempty valid parked bytes. It expires strictly after
3600 seconds, silently drops a missing trade, retains stale, releases verified
claims with their original birth time, and creates a personal `park_lost`
courtesy journal note for expiry/contradiction.
Release has no receipt check: the outer caller still gates it.

The source must combine all raw ports for accepted `ClaimVerifier`,
`OutboxJournal` and `LifecycleIdentity`, plus `park_exists`, `park_text`,
`atomic_mkdir`, `atomic_mkstemp`, `atomic_fdopen`, `atomic_fsync`,
`atomic_replace`, `atomic_unlink` and `format_il_clock`. These are raw offline
bytes/handles/clocks/state/effect ports, never injected final gate, receipt,
verifier, queue or parked-state verdicts. The atomic port sequence preserves
source cleanup but does not claim OS durability or cross-process semantics.

`check_lifecycle_gate_park_source_parity.py --source-root <retained-root>`
checks the pinned source projection plus actual claim-verifier, outbox-journal
and lifecycle-identity audit graph. Success keeps replay/training readiness
false. It does not certify full caller order, causal availability, historical
replay, labels, dataset construction, model training, promotion, notification
delivery or broker execution.
