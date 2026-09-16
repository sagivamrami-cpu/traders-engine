# Lifecycle identity / receipt reader

Status: accepted after both task and final combined reviews; see
`agent-exchange/status/2026-09-10T201630Z-codex-lifecycle-identity.md`.
Not a causal store or actual delivery service.

```python
from trading_system.tree_replay._vendor.lifecycle_identity import LifecycleIdentity

identity = LifecycleIdentity(raw_source)  # one instance per simulated process
delivered = identity._group_has(trade)
context = identity.context(message_text, state=tracker_rows)
```

The private reader requires receipt_stat(), receipt_text(*,encoding),
queue_exists(path), queue_text(path,*,encoding), load() and now_epoch(). These
are raw evidence/clock ports, not precomputed receipt/matching verdicts. No
network/file defaults or write/send methods are present. Queue paths are
logical chart-desk/out/group_queue paths; they are not automatically read from
the live checkout. A causal provider must restrict evidence to available time.

Actual source text matching, geometry identity and receipt rules are retained:
symbol/side, entry then stop then state fallback, named-level disambiguation,
OPEN-before-PENDING fallback and ambiguity. Thread context additionally requires
the original lifecycle headline and entry tolerance0.011; generic matching
uses0.02. A matched message is not proof of a price event or economic outcome.

Receipt matching requires symbol/side/rounded entry/style/geometry ID and
delivery timestamp >= trade send time minus120seconds. If trade ID is absent,
the actual original geometry hash is computed. Legacy receipts use the named
queue file (done before root), offering its own geometry under all three
source styles; they do not guess an intraday-only identity.

Receipt cache is per reader/process, initially mtime0/empty keys. Every call
stats; unchanged mtime reuses prior keys even if raw text changed. Initial
mtime0 therefore does not read. Failed reads do not update the cache. This is
the original source policy, not a newly designed historical cache. Preserve
reader lifetime in a future process/checkpoint model; don't reset each call.

Malformed JSON lines are skipped; structurally malformed parsed rows may raise
as in source. Missing stat/read OSError fails receipt qualification. Source
has no future-receipt upper bound: downstream causal evidence is still required.
context uses supplied state without loading, and reads its clock only when
returning an actual snapshot. It does not create a final immutable dataset row.

Verification:
`python -B -m pytest tests/tree_replay/test_lifecycle_identity.py tests/tree_spec/test_lifecycle_identity_source.py tests/tree_replay/test_tracker_admission.py -q --tb=short -p no:cacheprovider`
passed208cases16.50s exit0:48runtime,54auditor,106existing dependency cases.
Normal missing-runtime47RED and missing-auditor54RED preceded implementation.
The additional same-entry stop-disambiguation regression also rejected a local
stop-disabled mutant. Test counts overlap earlier component runs.

`python -B tools/check_lifecycle_identity_source_parity.py --source-root <retained-checkout-parent>`
emits JSON and exits0 for VERIFIED or2 for BLOCKED. It independently verifies
both original blobs/commit/baseline, ordered signatures and exact full runtime
projection, plus actual inherited canonicalization/geometry source proof. It
does not import or execute original or replay modules. Both readiness flags
remain false; source parity is not end-to-end historical replay certification.

Following work: actual claim gate/parking/retry and outbox journal, original
resolver/caller, causal artifact/feed providers, remaining producers and full
simulation/dataset/model/evaluation. No market action or training readiness.
