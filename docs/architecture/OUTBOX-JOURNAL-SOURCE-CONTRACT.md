# Original outbox journal over offline effects

Architectural continuation of approved master C/D. The next gate/park/resolver
must persist messages through this actual journal, not a supplied final queue.
See LIFECYCLE-CLAIM-PERSISTENCE-INTAKE.md for the full caller dependency chain.
No new trading rule, delivery policy or human economic decision is introduced.

## Source authority and choice

chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9,
chartdesk/outbox.py blob1cf608f81e30c82ddd83b211a0ca743133699e45.
Original text only; never import it, point STORE at a real queue or send.
Retain entire selected function bodies with enumerated raw effect substitutions.
This follows the accepted private reader pattern and enables later actual gate
composition. Importing the original would expose live IO; recreating just an
abstract enqueue would lose original deduplication/ownership/ordering semantics.

## Runtime shape

Create `_vendor/outbox_journal.py`. Prefix imports, in order:
future annotations, hashlib, json, contextmanager, sys, Path/PurePosixPath,
and actual LifecycleIdentity plus identity from lifecycle_identity.
`STORE = PurePosixPath('chart-desk/out/outbox.jsonl')` is a logical key, not an
OS destination. Keep original LATE_AFTER_S assignment and pure `_eid`,
`_append_lock_path`, `_merge` in source relative order. They perform no IO.

`OutboxJournal(source)` initializes self.source, self.threads=LifecycleIdentity(source),
and fresh self._BORN={} only; no clock/read/write in constructor. Later gate
composition will share journal.threads for process-local receipt cache ownership.
Never accept final thread/match/queue verdict providers in place of these readers.

Methods retain exact source arguments, annotations, defaults and decorators,
adding only self: _rows, _append_lock, _write, _append, _last_states,
remember_born, enqueue, _mark, pending, resolve, resolve_text, in source order.
_append_lock retains @contextmanager. Full source signatures must be pinned
independently before projection; _BORN's original empty annotated dictionary
must be checked before specialization to an instance dictionary.

## Allowed substitutions

All substitutions are scoped to named functions with independent exact counts.
Each expression occurs once unless a larger count is explicitly stated below.

- _rows: STORE.exists() -> self.source.journal_exists();
  STORE.read_text(encoding='utf-8') -> self.source.journal_text(encoding='utf-8').
- _append_lock: delete local `from . import filelock`; replace
  STORE.parent.mkdir(parents=True,exist_ok=True) with
  self.source.mkdir(STORE.parent.as_posix(),parents=True,exist_ok=True);
  open(_append_lock_path(),'a+') with
  self.source.open_append_lock(_append_lock_path().as_posix(),'a+');
  filelock.try_acquire(lk,timeout=None) -> self.source.try_acquire(lk,timeout=None);
  filelock.release(lk) -> self.source.release(lk).
- _write: source live-store/test guard -> self.source.assert_offline();
  parent mkdir as above; STORE.open('a',encoding='utf-8') ->
  self.source.open_journal('a',encoding='utf-8'). Keep exact JSON serialization
  and newline write inside the original context manager. The mandatory offline
  guard is an effect-boundary check, not a source economic or delivery verdict.
- _append: _append_lock() -> self._append_lock(); _write(row) -> self._write(row).
- _last_states: _rows() -> self._rows(), retaining real pure _merge.
- remember_born and enqueue: each original _BORN name -> self._BORN, exactly one
  occurrence per function. Keep original float conversion/pop-before-lock.
- enqueue: time.time() -> self.source.now_epoch(); delete trade_threads import;
  trade_threads.identity(text) -> identity(text);
  trade_threads.context(text) -> self.threads.context(text);
  _append_lock() -> self._append_lock(); _last_states() -> self._last_states();
  all three _write calls -> self._write, preserving each distinct argument AST.
- _mark: time.time() -> self.source.now_epoch(); _append(row) -> self._append(row).
- pending: _last_states() -> self._last_states().
- resolve: _mark(eid,'RESOLVED',why=why) -> self._mark(eid,'RESOLVED',why=why).
- resolve_text: pending() -> self.pending(); resolve(ev['id'],why) ->
  self.resolve(ev['id'],why).

No broad identifier renaming, no source function execution during extraction,
and no port supplying parsed/merged/final journal rows.

## Raw effect interface and scope

source must implement now_epoch(), journal_exists(), journal_text(*,encoding),
mkdir(path,*,parents,exist_ok), open_append_lock(path,mode),
try_acquire(handle,*,timeout), release(handle), assert_offline(),
open_journal(mode,*,encoding), and load() for actual thread context.
Lock/file open ports return context managers. Journal handle supports write(str).
The fixture/causal provider records exact ordering and makes appended bytes
available to subsequent raw reads. Do not supply a pre-decided queue state.
All effect ports must be explicitly supplied and offline-only; no fallback IO.
assert_offline raises before the physical write path if its sink is not offline.
This kernel does not prove provider isolation, OS locking, crash durability,
fsync or exactly-once delivery. No live-store test bypass is provided.

## Behavioral acceptance

Use raw in-memory JSONL, real actual identity/context and operation traces.
Expected event IDs must be literal independently calculated minute/text hashes.
Required cases:

1. Invalid nonstring/blank text rejected before clock/load/lock/write; stderr
   captured as asserted source behavior, not unhandled test output.
2. Actual group headline context uses two independent clock reads in order;
   supplied trade_context avoids load/second clock; non-group/no-head avoids it.
3. New journal row: exact id/ts/text/destination/kind/PENDING/zero attempts/
   false sent flags, optional real reply/context and born. Literal expected rows.
4. Same-ID DELIVERED/RESOLVED never resurrect; PENDING repeat never resets
   attempts/sent flags; personal-to-group upgrades preserve original timestamp.
5. Exact-text cross-minute dedupe at600 seconds, new row just after600;
   different text not deduped; source iteration winner retained.
6. Merge retains original ts and latest state/last_ts. Pending oldest-first,
   malformed payload retained for later resolution, orphan no-text skipped.
   Blank/torn JSON skipped; parsed malformed rows and read errors not hidden.
7. remember_born retains original claim time only if truthy and older; consumes
   even for duplicate/terminal enqueue as original. Separate instances isolated.
8. Read/decision/write all under one separate append lock, no reacquisition by
   _write; try_acquire timeoutNone exact; release on reader/write failure;
   acquire failure does not call release; refusal to use non-offline sink fails.
9. resolve and resolve_text append actual RESOLVED/why under a new clock/lock;
   exact-text only, return correct count, no fabricated delivery/trade exit.

## Independent proof and following work

Create tree_spec/outbox_journal_source.py, tools/check_outbox_journal_source_parity.py
and source mutation tests. Pin source HEAD/root/baseline/blob, selected symbols,
signature/decorator/order, initial _BORN and600-second assignment. Full projected
runtime AST includes imports/logical STORE/constructor and actual identity
composition; audit_lifecycle_identity_source supplies inherited source proof.
Mutation tests must exercise raw dispatch, actual dependency drift, child errors,
guard removal, lock ordering/release and deduplication without original imports.
CLI explicit retained parent, JSON0/2, unrelated cwd and inert import guard.
Replay/training readiness remain false even when proof succeeds.

After task/final acceptance: actual gate/parking/retry/atomic parked-store policy,
then original bar/live resolver/market-watch caller, causal artifact/operation
providers/checkpoints and all remaining master work. This is not a substitute
for those components, a historical dataset or a trained/profitable model.
