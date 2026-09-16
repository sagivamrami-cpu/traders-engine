# Agent Exchange Review

Reviewer: Codex independent Task1 reviewer

Request: agent-exchange/inbox/codex/2026-09-09T170600Z-watch-storage-review.md

Target request: agent-exchange/inbox/codex/2026-09-09T170600Z-watch-storage-review.md

Created at: 2026-09-09

Status: REVIEW_READY_FOR_CODEX

Verdict: Task1 specification PASS; Task1 code quality PASS. No concrete Critical,
Important, or Minor defect found. This is a Task1 review recommendation, not
combined component acceptance or certification of full-loop source parity.

## Scope and evidence

Read AGENTS.md, exchange README/protocol, own inbox listing and the exact request;
the full watch-state contract, usage, implementation plan, progress ledger and
Task1 new-file package. Applied the requested code-reviewer template directly.
Read all four actual files, not just the package, plus the inherited
TrackerStateSeed/_MemoryBackend and ReplayClock implementations.

Main HEAD is c1b6071633c55376c64f0a98ece843706f420f49. The four review targets are
untracked; ordinary git diff does not include their content. Actual file hashes
match the package's advertised new-file hashes:

| Actual file | Git blob hash |
| --- | --- |
| trading_system/tree_replay/_vendor/watch_storage.py | 0dc71cdfd1bebc45d23f3c1ea5e0614a1c8e5b21 |
| trading_system/tree_replay/watch_storage.py | bdaa43fbdc7354feb252e58397132e0146718b2b |
| tests/tree_replay/test_watch_storage.py | 681c6829091b81f4001fba605aade8dc56292a40 |
| docs/architecture/WATCH-STATE-BINDING-USAGE.md | 7868d4ef69d925a0c2277eb05b3227713e17cec8 |

Read literal source statements and surrounding control flow from retained
`C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk/scripts/market_watch.py`:

```python
# 494
st = json.loads(STATE.read_text()) if STATE.exists() else {}
# 904-905
STATE.parent.mkdir(exist_ok=True)
STATE.write_text(json.dumps(st))
# 1599-1600
STATE.write_text(json.dumps(st))
return 0
```

Read-only git checks confirmed retained HEAD
`68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9` and actual source blob
`f530fbe82cffbaf831c7a7725c7a9bf6143e6b8b`. Retained source was never imported,
compiled or executed. Task2 auditor implementation and mutation-suite development
were not duplicated or reviewed.

## Strengths

- `_vendor/watch_storage.py:9` preserves conditional exists/read/parse behavior
  and returns parsed roots unchanged. Lines 13 and 17 preserve both separate
  source write boundaries, including mkdir only before the first write and
  default json.dumps behavior at each write.
- `watch_storage.py:17` reuses causal guards while defining direct completed
  writes. Watch saves do not invoke tracker reread, shrink, quarantine, creation
  forensics or atomic-write policy. Encoding validation precedes image mutation.
- `watch_storage.py:32` requires the exact watch seed and valid clock binding.
  Wrapped operations retain outer errors as well as guarded child attempts.
  The inherited guard checks publication and coverage against current shared
  time on each operation, including saves and snapshots.
- `watch_storage.py:50` snapshots the persisted text/status, with current
  observed/available time and unchanged coverage. Parsed caller objects and
  returned traces cannot mutate that saved image. Source JSON root/default
  semantics, deletion, serialization failure and the two-save restart window
  are exercised by the actual tests.
- The usage explicitly limits the adapter to completed in-memory writes and
  one artifact handoff. It makes no torn-write recovery, OS permission, atomic
  transaction, complete checkpoint or full caller-order claim.

## Issues

### Critical

None found.

### Important

None found.

### Minor

None found. No speculative requirement is promoted to a defect.

## Verification reviewed

Fresh focused test command, exit 0: **32 passed in 0.08s**.

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -B -m pytest tests/tree_replay/test_watch_storage.py -q --tb=short -p no:cacheprovider
```

Fresh inline synthetic probes used a PowerShell single-quoted here-string piped
to `python -B -`, with the same no-bytecode setting. Exit 0; all seven groups
passed without creating probe files:

1. For each of load, both saves and snapshot: seed observed at T, publication
   T+2s, coverage T+10s; reject at T without image mutation, succeed at T+2s,
   reject at T+10s+1us without changing the last image. This independently checks
   publication delay distinct from observation time and recovery on one clock.
2. Circular list serialization through each save raises ValueError, preserves
   previous text and retains the outer error. Only the first save records mkdir;
   neither reaches write_text.
3. NaN, positive/negative infinity and a lone surrogate retain Python source
   JSON defaults; serialized text equals json.dumps of the supplied payload,
   and load recovers the expected values. No stricter JSON policy is invented.
4. Supplied whitespace and duplicate-key text remains exact through load and
   snapshot; explicit save alone performs source reserialization.
5. ABSENT/UNREADABLE snapshots preserve status, absent text, seed identity,
   exact WatchStateSeed type and original coverage.
6. Subclasses of WatchStateSeed and ReplayClock are rejected at construction.
7. Empty identity, invalid status/text combinations, unencodable supplied text
   and reversed observation/publication/coverage ordering are rejected.

Read-only `git rev-parse HEAD`, retained-repository `git rev-parse HEAD`,
`git hash-object` on retained source and all four targets, `git status --short`,
and scoped `git diff` were inspected. Scoped `git diff --check` exited 0 but is
not claimed as content validation of untracked files; actual full-file reads
and hashes supply that evidence.

The ledger's baseline 69, normal RED 32, and combined 101 results are historical
implementation claims, not independently rerun results in this review. No broad
suite or Task2 audit was run. Test caches and bytecode writes were disabled.

## Open questions

None blocking Task1. Historical directory/write failures, partial-write effects,
the watch lock, caller ordering and complete checkpoint semantics remain explicit
out-of-scope work, not capabilities established by these passing tests.

## Recommendations

Proceed to the controller's separate Task2 source audit and combined component
review. No Task1 code revision is requested. Preserve the documented completed-
write and artifact-only limits when integrating the original caller later.

## Assessment

Ready to merge? **Yes for the reviewed Task1 scope**, subject to the planned
Task2 audit and combined acceptance before accepting the overall component.
The actual implementation matches the scoped source statements and causal
contract; focused tests and additional edge probes found no semantic, temporal
or persistence defect. Only this requested report was written, via apply_patch;
no code edits, nested agents, source execution, live IO, commits or cleanup.
