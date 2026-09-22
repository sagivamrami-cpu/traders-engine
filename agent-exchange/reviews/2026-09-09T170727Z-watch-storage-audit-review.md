# Agent Exchange Review

Reviewer: Codex independent Task2 watch-source audit reviewer

Target request: agent-exchange/inbox/codex/2026-09-09T170727Z-watch-storage-audit-review.md

Request: agent-exchange/inbox/codex/2026-09-09T170727Z-watch-storage-audit-review.md

Created at: 2026-09-09T17:09:19Z

Status: REVIEW_READY_FOR_CODEX

Verdict: PASS for Task2 specification and code quality; no actionable findings.

## Scope and evidence

Read startup/protocol, the scoped inbox request, complete WATCH-STATE-BINDING-CONTRACT.md and implementation plan, Task2 full-file package/report, all three actual new files, actual vendor/watch_storage.py, and the imported AST/Git helpers. Reviewed actual untracked content, not an empty commit diff. Base and current HEAD are c1b6071633c55376c64f0a98ece843706f420f49. Existing unrelated changes were inspected and preserved.

Independently read retained chart-desk/scripts/market_watch.py statements at lines 494, 904, 905 and 1599, including their surrounding boundaries and final return at 1600. Read-only Git identity check returned commit 68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9 and HEAD:scripts/market_watch.py blob f530fbe82cffbaf831c7a7725c7a9bf6143e6b8b. The baseline chart-desk pin agrees. Source was only read/parsed; no retained source was imported, compiled or executed.

## Strengths

- trading_system/tree_spec/watch_storage_source.py:12 fixes commit/blob authority independently of the baseline. The baseline can invalidate certification but cannot redefine its pin. Root and HEAD checks precede comparison; normalized source content must match the fixed blob.
- trading_system/tree_spec/watch_storage_source.py:19 derives the bodies from actual source AST nodes. Exact cardinality is one load, one directory call and two writes. Both write occurrences are retained separately; source order, immediate mkdir-before-first-write and final-write-before-return boundaries are enforced.
- trading_system/tree_spec/watch_storage_source.py:76 compares the complete candidate module after removing only its leading module docstring. Imports, constructor, signatures, decorators, additional code and all method bodies remain in the comparison. The expectation is not copied from the candidate or accepted from a manifest.
- tools/check_watch_storage_source_parity.py:13 requires an explicit retained-source parent and maps certification to VERIFIED/0 or BLOCKED/2. Both readiness flags remain false.

## Issues

Critical: None.

Important: None.

Minor: None raised for this scoped review.

Findings: No concrete missed behavioral mutation survived the additional probes below.

## Verification reviewed

PASS: 18 focused audit tests, independently rerun in 3.71s, terminal exit 0. To honor the read-only constraint, disabled bytecode/cache writes and replaced only pytest's temporary-directory fixture with the already existing OS temporary directory. Test bodies were unchanged; their missing-source/runtime and unrelated-cwd CLI checks passed. Exact invocation:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
@'
from pathlib import Path
import tempfile
import pytest
class ReadOnlyFixtures:
    @pytest.fixture
    def tmp_path(self):
        return Path(tempfile.gettempdir())
raise SystemExit(pytest.main(['tests/tree_spec/test_watch_storage_source.py', '-q', '--tb=short', '-p', 'no:cacheprovider'], plugins=[ReadOnlyFixtures()]))
'@ | python -B -
```

PASS: Additional read-only stdin harness executed with `python -B -`, using `unittest.mock.patch` on Path.read_text or the auditor's _git helper. No mutations were written to disk or executed as candidate code. All eleven cases returned BLOCKED:

1. Swap the two save method names/bodies.
2. Replace the final write with pass.
3. Remove the load method.
4. Move first-save mkdir after write.
5. Append an extra module-level call.
6. Add a class decorator.
7. Return the wrong repository top-level while preserving the correct HEAD.
8. Move source mkdir after the first write.
9. Insert a source statement between mkdir and the first write.
10. Insert a source statement between the final write and return 0.
11. Duplicate the final source write.

For cases 8-11, additionally passed the mutated inert text directly to _projection, independently of blob rejection: cases 8/9 raised WATCH_PERSISTENCE_ORDER_MISMATCH, case 10 WATCH_FINAL_PERSISTENCE_BOUNDARY_MISMATCH, and case 11 WATCH_PERSISTENCE_CARDINALITY_MISMATCH. This verifies the extraction guards themselves, rather than crediting only the hash check. No source execution was involved.

PASS: `git diff --check` for tracked changes (only existing CRLF warnings); actual new-file review was separate because the files are untracked. The implementation report's 174 combined tests and original RED history were read, not independently rerun/reconstructed; the controller owns broader acceptance.

Reviewed SHA256 identities, unchanged on the final reread:

| File | SHA256 |
| --- | --- |
| trading_system/tree_spec/watch_storage_source.py | f784dc574bd02222895112995a1f6f674ac46440add509fbabc36b435d9f3fc8 |
| tools/check_watch_storage_source_parity.py | 62238bcc9a40482840a6da5dae53d22c98722e3772c7afc7c881ae3b543eb932 |
| tests/tree_spec/test_watch_storage_source.py | 3ebf9c15664574953521a74c358cbe56119cdafa40eb100f9ad59751c81bb135 |
| trading_system/tree_replay/_vendor/watch_storage.py | 666fc8593c9b057bc45a8d3ddd99e3905557ed8721461958b3e56769c3f171e7 |

## Recommendations and assessment

Ready for Task2 acceptance: Yes. Fixed source identity, independent extraction and complete candidate comparison support the claimed three-projection subset. The additional probes found no missed concrete mutation requiring a revision.

Open questions/blockers: None within Task2. Tests depend on an available pinned source checkout (TR_TREE_SOURCE_ROOT can supply it).

Recommended next action: Controller may use this review in its component acceptance. This review does not accept the causal wrapper or certify caller ordering, watch locks, full-loop replay, data coverage, labels or training readiness. No other reports/inbox/code were edited, no nested agents used, and no live IO or broad tests performed.
