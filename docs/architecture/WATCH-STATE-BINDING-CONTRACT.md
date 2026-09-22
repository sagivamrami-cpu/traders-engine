# Causal watch-state persistence contract

Continuation of approved master C architecture, not a new trading-policy choice.
Keep heterogeneous watch state and its two original persistence boundaries separate
from tracker state. Source: pinned chart-desk scripts/market_watch.py main494,
904-905,1599; commit68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9 and blob
f530fbe82cffbaf831c7a7725c7a9bf6143e6b8b. Retained source is inert audit input.

## Source projection

Private WatchStorage(source) exposes load(), save_before_producers(st), save_final(st).
Extract original top-level main statements: `st = json.loads(STATE.read_text())
if STATE.exists() else {}` plus returnst for load; parent.mkdir(exist_ok=True)
and STATE.write_text(json.dumps(st)) for first save; the final identical write
without mkdir for final save. Only STATE IO calls are replaced with explicit ports.
Do not inject sorting, indent, ensure_asciiFalse, shrink protection, quarantine,
atomic replacement, creation forensics or dict-root validation. Scalar/list/null
JSON is returned unchanged; actual later source consumers can fail on it.

Independent audit pins commit/blob/baseline, extracts these exact AST statements
from main with cardinality and source-order checks, compares the whole candidate
module including allowed imports/class/constructor. Check both save occurrences,
not a synthetic hand-written specification that ignores one source write. Audit
never compiles/imports/executes retained scripts. CLI requires source-root and
returns exit0 VERIFIED or2 BLOCKED; readiness remains false.

## Causal wrapper

WatchStateSeed is a distinct exact frozen subclass of TrackerStateSeed sharing
validated identity, UTF8 text, UTC observed/available/covered times and statuses.
CausalWatchStorage(seed, decision_time, clock=None) validates exact seed and
optional exact ReplayClock binding. Reuse accepted causal text guard through a
private backend subclass, but implement direct completed write_text and directory
attempt ports, never route watch writes through TrackerStorage.save or claim
atomicity. No filesystem, threads, external accounts or actual directories.

UNKNOWN/unpublished/expired inputs block calls with retained traces; known absent
load returns{}, known unreadable raises, malformed JSON raises. Known unreadable
content can be overwritten, matching lack of prior-state-read in the source write.
Directory creation is a recorded successful in-memory port attempt within known
coverage, not evidence of historical permissions. Serialization failure happens
after that first mkdir and before write; existing persisted text remains intact.

load returns freshly parsed values, so caller mutation does not persist until one
of the two explicit saves. Both saves serialize defaults, preserving insertion
order, scalar/object values and deletions as complete images. A snapshot emits
an exact WatchStateSeed with current operation-time observed/available and original
coverage; snapshot returns only the last completed persisted image, never a caller
object still being edited. Shared clock advances retain the image; guards check
coverage at each use. trace is detached and includes parent and child failures.

This is one artifact handoff, not complete checkpoint/resume or recovery from an
actual torn OS write. Historical partial writes must be supplied as explicit text
evidence. Watch lock, caller order, scheduling/publications and lifecycle remain
separate work; do not add a watch channel to the admission context in this task.

## Acceptance

Tests must detect accidental tracker shrink reuse, root normalization, sorted/
Unicode/indent serialization changes, early publication of unsaved changes,
missing deletion, wrong first/final directory order, missing temporal guards,
trace aliasing and constructor ambiguity. Audit mutation tests must reject source
pin/blob/runtime/import/body drift and missing files; test CLI from unrelated cwd.
Task review and final combined component review precede acceptance. No labels,
dataset/model, live data/notifications, commits, cleanup or full-plan completion.
