# Causal tracker storage binding

Part of approved master C, after admission frames. This implements original
tracker load/save behavior over an explicitly supplied in-memory source artifact.
It does not implement OS lock contention, full market-watch state, quotes, logs,
source lifecycle, economic outcomes or training. Those remain required next work.

## Source behavior and adaptation

Pinned chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9,
chartdesk/tracker.py blob b616b34022e436545d8c1daf85eced51614fd74e.
Recover whole _load/_save methods into private TrackerStorage(source). Explicit
ports replace filesystem, live-test-target test, clock, creation forensic sink
and atomic write. Keep exact source branches, exceptions, serialization and order:
absent ->{}, unreadable load raises; save rereads current contents; cur=None or
loss>len(cur)//2 when len(cur)>=4 quarantines then raises. allow_shrink=True
bypasses reread/creation/quarantine checks, not causal input coverage. JSON remains
unsorted, ensure_ascii=False, indent=1, source default NaN behavior. Corrupt or
non-object source text is not silently normalized into an empty dict.

The runtime has no real Path, disk, network, global state or wall-clock access.
Original live-test guard is retained through a port; the concrete in-memory
backend cannot designate a live target. Atomic write becomes one replacement of
immutable text. Quarantine becomes a separate in-memory artifact with original
open_trades.rejected-<int epoch> naming and same-second overwrite behavior.
This models completed source writes, not torn writes, OS I/O faults or concurrent
writers. Fault-injected port tests verify wrapper failure propagation separately.

Creation forensics preserves set-difference before the best-effort boundary,
per-new-key record extraction (entry/stop/state/variant/revived_from_ts), timestamp
and partial emission before a bad row. Historical PID/argv/stack are not invented:
effects are explicitly marked replay_creation_effect. They are research evidence,
not byte-identical source trade_creations.jsonl. Order of set iteration is not a
trading invariant. Root tracker key order IS preserved by raw JSON text and load.

## Causal input and exact interface

TrackerStateSeed: frozen keyword-only dataclass with seed_id:str, source:str,
observed_at:datetime, available_at:datetime, covered_through:datetime,
status:str in PRESENT/ABSENT/UNREADABLE/UNKNOWN, text:str|None. Exact UTF-8
identities/text, aware microsecond-exact UTC times; observed<=available<=covered.
PRESENT requires exact text (including malformed JSON); all others requireNone.
Coverage attests an external-input snapshot with no unrepresented external
changes through covered_through; generated replay saves may replace it locally.
It is not independently certified data and payload timestamps are not rewritten.

CausalTrackerStorage(*,seed:TrackerStateSeed,decision_time:datetime): exact seed
type/revalidation, actual UTC time. load()/save(d,allow_shrink=False) via original
methods; unavailable before publication/after coverage or UNKNOWN raises
StateUnavailable, never returns{} and never changes stored text. UNREADABLE is
a known existing file with read failure: load raises OSError; normal save creates
quarantine then refuses; explicit allow_shrink can replace it as in source.

snapshot()->TrackerStateSeed returns current artifact at the fixed decision time,
available_at=T, same covered_through, identity/source. It requires available input
and preserves status until a successful save. This is a state handoff, not a full
replay checkpoint; source logs, lifecycle, clock/lock state and other artifacts
must be checkpointed by the later complete loop. snapshot supplied to another
instance can continue at a later covered time. No implicit time advance/cache.
trace and creation_effects/quarantine_artifacts are detached read-only snapshots
of ordered operations/effects; modifying a returned object cannot change storage.
Source reads and failed effects remain observable; no public ready flag or model.

## Verification

RED tests before runtime. Original tracker has_open/_record_locked consume this
store in integration with other ports controlled; no fake successful storage sink.
Verify absent/corrupt/null/nonobject, key order/detachment, exact shrink boundaries,
allow_shrink, reread after intervening save, quarantine-before-error, same-second
replacement and creation-forensics boundaries. Trace missing coverage through
source catch; future/late/expired seed cannot masquerade as an empty desk.
Test source wrapper guard, read/quarantine/atomic-write failures at actual ports.
Independent AST auditor pins repo+blob and requires full module projection of
_load/_save with enumerated exact substitutions, never executes original source.
Mutation tests must catch changed shrink threshold, removed reread and extra code.
Task and full component review before use by complete loop. No domain policy change.
