# Original lifecycle text, receipt and thread identity

Architectural continuation of approved master C/D, not a new trading choice.
LIFECYCLE-CLAIM-PERSISTENCE-INTAKE.md records the full following gate/persistence
scope; this dependency supplies actual identity/receipt reads before that gate.
No supplied final receipt verdict, trade matching answer or thread snapshot.

## Design and alternatives

Implement one private LifecycleIdentity(source) reader that owns process-local
receipt cache and uses pure original matching functions. It combines the small
trade_threads.context consumer with tracker matching to avoid their original
circular module import. Preserve complete source function bodies through
enumerated raw IO/call substitutions and independently audit them.
Direct original imports are unsuitable because they initialize live paths/IO.
Duplicating matching separately for thread context would split one source of
truth; both must call the same recovered original matcher. This new reader is
not itself a causal artifact store or group delivery service.

Sources at chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9:
tracker.py blobb616b34022e436545d8c1daf85eced51614fd74e;
trade_threads.py blobb05cfcf45cb420c40254154e80d3792a7b1685b9.
Original source read/parse only. No changes to existing accepted source modules.

## Runtime files and exact interfaces

`_vendor/lifecycle_identity.py` contains original pure `_fmt`, `_side_from_text`,
`_prices_in_text`, `_text_has_price`, `_trade_has_named_level_in_text`,
`_match_trade_for_text`, plus trade_threads.HEAD and identity. Keep source
function order within each projection; prefix imports are future annotations,
json, re, pandas and PurePosixPath plus actual basis_symbols canonicalization
and tracker_admission._trade_identity. No parser rewrite or new tolerances.

LifecycleIdentity constructor stores source and a new `_receipt_cache` dict
`{'mtime': 0, 'keys': set()}` only, with no reads or clocks. Each instance
represents one source process; do not reset cache per gate call or share a
mutable global across readers. Methods retain source names/signatures plus self:
`_receipt_from_queue_file(r: dict) -> dict`, `_group_has(t: dict) -> bool`,
`context(text, state=None)`. Preserve the original misleading migration return
annotation (actual result is a list); no cleanup changing source signature.

`_receipt_from_queue_file` replaces only source ROOT with
PurePosixPath('chart-desk'), f.exists with
self.source.queue_exists(f.as_posix()), and f.read_text(encoding='utf-8') with
self.source.queue_text(f.as_posix(), encoding='utf-8'). Everything else remains:
.json restriction, done-first order, fallback only on absent, read failure
handling and all three styles computed through actual _trade_identity.

`_group_has` replaces `_RECEIPTS.stat()` with self.source.receipt_stat(),
`_RECEIPTS.read_text(encoding='utf-8')` with
self.source.receipt_text(encoding='utf-8'), all cache accesses with self cache,
and migration call with self._receipt_from_queue_file(r). Raw stat must provide
st_mtime_ns. Keep canonicalization and actual geometry identity functions.
No synthetic receipt timestamps or cache invalidation defaults.

`context` removes its original local `from . import tracker`; maps tracker._load
to self.source.load, tracker._match_trade_for_text to the recovered pure matcher,
and time.time to self.source.now_epoch. Keep identity, field tuple, comparison,
state override behavior, returned geometry and independent clock exactly.

Required raw source ports are receipt_stat(), receipt_text(*,encoding),
queue_exists(path), queue_text(path,*,encoding), load(), now_epoch(). They supply
only raw evidence, not group_has/context/matching. No default file/network reads
or receipt write API. Pure helper functions have no provider dependency.

## Required behavioral proof

Actual text matching: entry versus stop/fallback priority; symbol and side;
ambiguous same entry resolved by target/stop; OPEN before PENDING fallback;
CANCELLED exclusion only in fallback; decimal-price regex and0.02 tolerance.
Thread context: original lifecycle marks and late prefix;0.011 entry guard;
supplied state avoids load; no identity returnsNone before load/clock; actual
clock only for a produced snapshot. Expected geometry is literal, not produced
by calling context/matcher to calculate its own expected result.

Raw receipt proof: absent stat failclosed, matching geometry/style/delivery
time, exact120second slack, older rejection, canonical symbols, missing trade
ID calculated from actual geometry, malformed lines versus malformed parsed
records, bad timestamps, ordered legacy queue fallback and three-style migration.
Use literal externally calculated geometry IDs or hand-built receipt geometry
fixtures, never a provider-final verdict. Show source cache reuses parsed keys
when mtime unchanged even if raw text differs, updates on changed mtime, retries
after read error and is isolated between instances. st_mtime_ns0 initial cache
must retain original no-read behavior. Record raw read/clock sequence.

## Independent proof and acceptance

`tree_spec/lifecycle_identity_source.py` independently pins both blobs/commit,
selected ordered source symbols and exact signatures/substitution counts.
Compare complete projected pure/module/class AST, including method bodies and
constructor/cache initializer. Actual inherited tracker admission audit verifies
canonicalization/geometry identity; a fabricated dependency verdict is not proof.
Propagate its blockers and missing authority. Keep readiness flags false.
`tools/check_lifecycle_identity_source_parity.py` uses explicit parentroot and
JSON0/2, works from unrelated cwd and never imports original/runtime modules.

Normal missing-runtime and missing-auditor RED; green real consumer tests and
source mutation tests; independent task/final reviews and recorded acceptance.
Candidate changes to cache scope/order, geometry identity, delivery slack,
matching priorities, thread tolerance and raw port dispatch must be detected.
Test actual nested identity dependency drift as well as local boundaries.

## Following scope stays mandatory

Next: actual gate/parking/retry and outbox enqueue/resolve journal composition
with ClaimVerifier, then bar/live resolver/caller and causal artifacts/scheduling.
No receipt write, Telegram send, OS durability/lock claim, economic result or
training readiness. Future receipt leakage is excluded by the eventual causal
provider, not by pretending source _group_has contains an upper timestamp gate.
