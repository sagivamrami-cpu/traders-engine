# Offline original outbox journal

Status: runtime, source audit and both task reviews are accepted; the combined
component final review is in intake. Not a delivery service or trade outcome.

```python
from trading_system.tree_replay._vendor.outbox_journal import OutboxJournal

journal = OutboxJournal(raw_source)  # one per simulated source process
event_id = journal.enqueue(text, to_group, trade_context=original_context)
pending = journal.pending()
```

This computes original minute/text IDs, reads actual raw JSONL and merges rows,
then performs enqueue/deduplication or resolution under its separate append lock.
Delivered/resolved same-minute IDs cannot be resurrected. Pending retries retain
attempt/sent flags; group upgrade and600-second cross-minute deduplication retain
original event timestamp. Resolution is a journal state, not an economic exit.

The process owns actual LifecycleIdentity for thread context and its own _BORN
memory. Claim birth is consumed before the lock, including duplicate/terminal
enqueue. Group headline context is computed before queue access, with an
independent clock; supplied context avoids tracker reload. Preserve process
lifetime when connecting future replay/checkpoint providers.

Raw source ports:
now_epoch(), load(), journal_exists(), journal_text(*,encoding),
mkdir(path,*,parents,exist_ok), open_append_lock(path,mode),
try_acquire(handle,*,timeout), release(handle), assert_offline(),
open_journal(mode,*,encoding). Open ports return context managers and journal
handles implement write(str). Raw writes must be visible to later journal reads.
Logical paths are chart-desk/out/outbox.jsonl and outbox.append.lock; no default
filesystem/network implementation exists. The offline guard precedes journal
writer opening, but lock setup occurs before it, just as the original guard
was inside _write. Every supplied effect port must already be offline-only.

Raw port provision is NOT proof of provider isolation, OS mutual exclusion,
crash durability, historical availability or successful delivery. No transport,
compactor, live-store override, flusher or receipt writer is included here.
Unknown/failed source IO must not be substituted with an empty success result.
Original JSON errors skip torn lines; malformed parsed rows/read errors may raise.

Verification: the controller ran
`python -B -m pytest tests/tree_replay/test_outbox_journal.py tests/tree_spec/test_outbox_journal_source.py tests/tree_replay/test_lifecycle_identity.py -q --tb=short -p no:cacheprovider`
with 140 passing cases in 22.38s. The explicit retained-source CLI
`tools/check_outbox_journal_source_parity.py --source-root <retained-root>`
returned VERIFIED with zero blockers through the real identity/tracker-admission
dependency graph. These proofs retain replay/training readiness false; combined
component acceptance is recorded separately after final-review intake.

Following work: gate/parking/retry/atomic parked store, resolver/caller and causal
providers, then all remaining master simulation/dataset/model/evaluation gates.
