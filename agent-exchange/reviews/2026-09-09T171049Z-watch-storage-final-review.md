# Agent Exchange Review

Reviewer: Codex independent final combined reviewer

Request: agent-exchange/inbox/codex/2026-09-09T171049Z-watch-storage-final-review.md

Target request: agent-exchange/inbox/codex/2026-09-09T171049Z-watch-storage-final-review.md

Created at: 2026-09-09T17:12:54Z

Status: REVIEW_READY_FOR_CODEX

Verdict: Combined specification PASS; combined code quality PASS. No actionable
Critical, Important or Minor findings. Recommend component acceptance by the
controller; this report is not full-loop, checkpoint or model acceptance.

## Scope and evidence

Read startup instructions, exchange README/protocol and own inbox; executed only
the requested final review. Read the complete watch contract, implementation
plan, usage, both full-file packages, progress ledger and Task2 report. Read both
prior reviews 170600Z/170727Z and their original requests, task acceptances
170816Z/171049Z, and shared-clock/context acceptance 170950Z and its usage.
Applied the code-reviewer checklist directly, without nested agents.

Read all seven actual files, including both test modules, and the inherited
TrackerStateSeed, _MemoryBackend, ReplayClock, tracker save implementation and
imported AST/Git helpers. Inspected git status and diff. HEAD is
c1b6071633c55376c64f0a98ece843706f420f49; all seven targets are untracked, so an
empty scoped git diff is not evidence of unchanged or absent implementation.
Actual full-file reads and these Git blob hashes match the packages and remained
unchanged on the final check:

| File | Git blob hash |
| --- | --- |
| trading_system/tree_replay/_vendor/watch_storage.py | 0dc71cdfd1bebc45d23f3c1ea5e0614a1c8e5b21 |
| trading_system/tree_replay/watch_storage.py | bdaa43fbdc7354feb252e58397132e0146718b2b |
| tests/tree_replay/test_watch_storage.py | 681c6829091b81f4001fba605aade8dc56292a40 |
| docs/architecture/WATCH-STATE-BINDING-USAGE.md | 7868d4ef69d925a0c2277eb05b3227713e17cec8 |
| trading_system/tree_spec/watch_storage_source.py | c6b9a97642a5460c540862d41c04c7a92ca22483 |
| tools/check_watch_storage_source_parity.py | 93536a2a025843e5da3f91375e91a05a6e0d40a6 |
| tests/tree_spec/test_watch_storage_source.py | 4fce0e2843bce0396c65fc1a728c6ef8a66a2e49 |

Independently read retained chart-desk/scripts/market_watch.py at lines 494,
904-905 and 1599-1600, including surrounding lock, detector and final producer
control flow. Retained parent:
`C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`.
Read-only Git checks confirmed commit
68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9 and HEAD source blob
f530fbe82cffbaf831c7a7725c7a9bf6143e6b8b. The auditor independently checked the
actual normalized source content. Retained source was read/AST-parsed only,
never imported, compiled or executed.

## Strengths

- `_vendor/watch_storage.py:9` preserves exists/read/default JSON loading and
  heterogeneous roots. Lines 13 and 17 preserve separate source saves, with
  mkdir only before the first serialization/write and original JSON defaults.
- `watch_storage.py:17` reuses temporal guards without calling tracker save.
  Its direct completed-write port validates encoding before changing text or
  status; tracker reread, shrink rejection, quarantine and creation effects do
  not leak into watch saves.
- `watch_storage.py:32` enforces the distinct exact seed and shared-clock
  binding. Lines 39-52 preserve parent/child failures, current operation-time
  guards and snapshots of the persisted image. Unsaved caller objects remain
  separate from prior handoffs and subsequent reloads.
- `tree_spec/watch_storage_source.py:19` derives all three projections from
  actual source nodes and checks cardinality, mkdir adjacency and final-return
  boundary. Lines 59-83 independently enforce source identity and compare the
  complete candidate AST, including constructor/imports/signatures/bodies.
  The CLI requires an explicit source root and keeps both readiness flags false.
- Usage states the completed-write and single-artifact limits explicitly;
  neither the audit nor wrapper claims to enforce complete caller ordering.

## Findings

Critical: None found.

Important: None found.

Minor: None raised. The source-checkout dependency is explicit and configurable
through TR_TREE_SOURCE_ROOT; existing cross-runner provisioning work is not a new
watch-storage correctness defect.

## Verification reviewed

Fresh focused runtime plus source-audit suite: **50 passed in 4.08s**, exit 0.
To honor report-only writes, disabled bytecode/cache output and supplied an
existing temporary directory for the two tests that only need an unrelated cwd
or missing paths. Test bodies were unchanged; preconditions checked that their
missing targets did not exist. Exact command:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
@'
from pathlib import Path
import tempfile
import pytest
class ReadOnlyFixtures:
    @pytest.fixture
    def tmp_path(self):
        p = Path(tempfile.gettempdir())
        assert not (p / 'chart-desk').exists()
        assert not (p / 'absent.py').exists()
        return p
raise SystemExit(pytest.main(['tests/tree_replay/test_watch_storage.py', 'tests/tree_spec/test_watch_storage_source.py', '-q', '--tb=short', '-p', 'no:cacheprovider'], plugins=[ReadOnlyFixtures()]))
'@ | python -B -
```

Additional synthetic combined probe: PASS, exit 0. Executed a single-quoted
PowerShell here-string through `python -B -`, without creating probe files:

1. Real CausalWatchStorage and CausalTrackerStorage shared one ReplayClock and
   equivalent four-key starting text. Watch first-save deletion of three keys
   succeeded. Tracker rejected the same deletion and retained its original
   text plus quarantine; watch had no tracker effects or tracker save operations.
2. At T+5s, modified the caller's nested episode and added an unserializable set.
   Final save raised TypeError and retained the first completed text. A fresh
   storage constructed from the snapshot loaded that first image. The outer
   failure trace used T+5s, not construction time.
3. At the inclusive T+10s coverage edge, final-save full deletion persisted `{}`
   while the earlier handoff remained independent. At T+10s+1us, watch load,
   both saves and snapshot all blocked without image mutation; the tracker with
   T+20s coverage still loaded correctly on that same clock.
4. For each save separately, controlled fault injection advanced the real clock
   just after normal JSON serialization and before write_text. The guarded
   child write and outer save both retained STATE_COVERAGE_EXPIRED failures;
   original persisted text remained intact. First save retained its successful
   mkdir attempt; final save had no mkdir. This probes child-guard composition,
   not historical operation timing or an implemented scheduler.
5. Reran the actual source auditor after these runtime probes: VERIFIED,
   exactly three projections, no blockers, ready_for_replay=false and
   ready_for_training=false. Focused tests separately exercised CLI success and
   blocked exits from the unrelated directory.

Read-only Git identity/hash checks and scoped status/diff completed. Final
`git diff --check` exited 0 with only existing LF/CRLF warnings; that check does
not cover untracked contents. The implementation's RED history, 174 combined
tests and subsequent controller runs are reviewed historical evidence, not
additional tests independently rerun here. Counts overlap. The controller owns
the current broad tree suite; this review neither duplicates nor reports it as
completed.

## Open questions and limitations

None blocking this component. Watch scheduling/publications, separate watch lock,
full caller/lifecycle, historical permission failures and partial OS writes are
outside the contract. The wrapper models completed in-memory writes only. Its
snapshot is one artifact handoff, not a whole checkpoint or atomic pass; matching
source statements does not prove complete caller order. Shared-clock composition
here does not establish a watch channel in CausalAdmissionContext. No economic
labels, feed coverage, full replay or training readiness follows from this review.

## Recommended next action and assessment

Ready for scoped component acceptance: Yes. The combined implementation matches
the persistence contract and pinned source subset; focused tests and independent
boundary probes found no concrete defect requiring revision. Controller should
record its acceptance using this report and its separately owned verification.
No implementation change is requested.

Only this requested report was written, via apply_patch. No runtime edits,
nested agents, inbox changes, commits, cleanup, network/data acquisition or
retained-source execution were performed.
