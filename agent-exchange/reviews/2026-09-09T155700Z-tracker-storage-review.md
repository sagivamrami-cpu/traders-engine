# Agent Exchange Review

Reviewer: Codex independent task reviewer

Target request: agent-exchange/inbox/codex/2026-09-09T155700Z-tracker-storage-review.md

Request: agent-exchange/inbox/codex/2026-09-09T155700Z-tracker-storage-review.md

Created at: 2026-09-09T15:59:07Z

Status: REVIEW_READY_FOR_CODEX

Verdict: WITH FIXES. Spec: one failed-effect observability requirement unmet. Quality: one Important issue; no Critical or separate Minor findings. Ready to merge/accept this component: with the tracing fix and focused regression coverage.

## Scope and strengths

Reviewed the full seven-file package against the named contract/plan, task report and progress ledger, after startup/inbox inspection and reading requesting-code-review/SKILL.md and code-reviewer.md. HEAD is c1b6071633c55376c64f0a98ece843706f420f49. All seven deliverables are untracked additions; review used their actual contents and the supplied package, not HEAD..HEAD:

- trading_system/tree_replay/_vendor/tracker_storage.py
- trading_system/tree_replay/tracker_storage.py
- trading_system/tree_spec/tracker_storage_source.py
- tools/check_tracker_storage_source_parity.py
- tests/tree_replay/test_tracker_storage.py
- tests/tree_spec/test_tracker_storage_source.py
- docs/architecture/TRACKER-STORAGE-BINDING-USAGE.md

The private wrapper preserves original _load/_save ordering: live-target guard, current-text reread, creation before shrink refusal, strict loss boundary, quarantine before refusal, and final unsorted JSON write. Malformed/null/nonobject input is not normalized. The auditor independently projects the full wrapper module and checks repository, baseline commit and source blob; mutation tests cover important branch changes and extra code.

The causal guard also wraps allow_shrink and snapshot, so unknown, unpublished or expired seeds cannot become an empty desk or a successful write. Snapshot observation/publication advances to the fixed decision time while retaining identity/source/coverage and raw root order. Returned artifacts and effects are detached. Real TrackerAdmission record/exposure and same-level selection exercise actual storage with explicitly controlled other ports. No source-consumer incompatibility was found in those inspected paths.

Compared original tracker.py _load (line 220), _audit_creation (231), and _save (260) with the adapter. Creation effects preserve the set-difference boundary, stop after a bad row and retain earlier emissions; historical process metadata is intentionally omitted and clearly labeled. The limitation of the AST audit to load/save, and the distinction between an artifact handoff and a full checkpoint, are accurately documented.

## Findings

### Critical

None found.

### Important

1. Swallowed creation-effect failures are reported as successful audit operations.

   File: trading_system/tree_replay/tracker_storage.py:133 (also :118 and :81).

   `_MemoryBackend.audit_creation` catches extraction/serialization/encoding exceptions inside `audit()` and returns normally. Consequently `call("audit_creation", audit)` marks the operation AVAILABLE with no exception or blocker. For a valid PRESENT `{}` seed, `save({"bad": 4})` succeeds and persists the row, correctly matching the source's best-effort behavior, but creation_effects is empty and every trace entry reports success. The AttributeError from the failed record extraction has disappeared. With several new rows, the same problem hides the reason only a prefix of creation effects was emitted.

   This conflicts with docs/architecture/TRACKER-STORAGE-BINDING-CONTRACT.md:62: "Source reads and failed effects remain observable." A consumer retaining the promised operation/effect evidence cannot distinguish a completed forensic attempt from a suppressed extraction failure. This is an evidence defect, not an incorrect save/refusal decision or a live-trading issue. The existing bad-record and unserializable-value tests assert save/effect behavior but do not assert visibility of the caught failure.

   Preserve the source catch and successful-save behavior, but trace each attempted effect inside that best-effort boundary (or record an equivalent explicit failure event before swallowing). Retain the exception type/reason and ordering, without fabricating a creation record. Add regressions for successful save after a bad row, serialization failure, and partial emission before a later bad row; assert both the retained effects and the failed trace entry. Do not turn forensic failure into a save veto.

### Minor

None separately raised.

## Verification reviewed

- Read the implementation evidence claiming 306 passing tests across the five named files, 59 new tests, and two verified source projections. These are implementer results, not independently reproduced suite results. No pytest suite was rerun, per the request.
- Independently ran `python -B tools/check_tracker_storage_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`: PASS, exit 0, VERIFIED for tracker._load and tracker._save, no blockers, replay/training readiness false. This does not audit backend effects.
- Ran a focused, file-free `python -B -` probe through PowerShell stdin because caught forensic-failure tracing was not covered. PASS assertions: partial emission stops at the bad row while save succeeds; returned trace mutation does not affect storage; snapshot retains seed identity/source/coverage and sets observed/available to T. FAIL, exit 1: expected an AttributeError in the trace after saving a scalar new row; none exists. The actual audit entry was `{"operation": "audit_creation", "decision_time": "2026-09-09T16:00:00+00:00", "status": "AVAILABLE", "exception_type": null, "blocker": null}`.
- Inspected git status and tracked diff; unrelated existing AGENTS.md/README.md changes and other untracked work were preserved. No implementation or test files were edited.

Minimal reproduction of the failed probe assertion (run via `python -B -`):

```python
from datetime import datetime, timezone
from trading_system.tree_replay.tracker_storage import TrackerStateSeed, CausalTrackerStorage
t = datetime(2026, 9, 9, 16, tzinfo=timezone.utc)
s = CausalTrackerStorage(seed=TrackerStateSeed(
    seed_id="review-synthetic", source="review-synthetic",
    observed_at=t, available_at=t, covered_through=t,
    status="PRESENT", text="{}"), decision_time=t)
s.save({"bad": 4})
assert s.load() == {"bad": 4}
assert s.creation_effects == []
assert any(e["exception_type"] == "AttributeError" for e in s.trace)
```

Original source parent: C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149. Pinned chart-desk commit 68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9; tracker.py blob b616b34022e436545d8c1daf85eced51614fd74e. Retained source was read/parsed, never imported or executed.

Open questions: none requiring a domain or human decision for this correction.

Recommended next action: fix the Important tracing gap, run focused regressions and obtain re-review before component acceptance. Broader quote/log/lock/caller-order research was not duplicated. This review does not certify complete replay, OS locking/atomicity, forensic byte parity, lifecycle, economic labels, model readiness, or live operations. No nested agents or other plan scratch were used; this review is the only authored file.
