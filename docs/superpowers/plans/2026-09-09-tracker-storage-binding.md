# Tracker storage binding implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development. Track checkbox steps.

**Goal:** Preserve source tracker load/save behavior on causal in-memory state.
**Architecture:** Private original method projection over explicit ports, backed
by a fixed-decision-time supplied text artifact; detached traces and state handoff.
**Tech Stack:** Python stdlib, existing _utc/TrackerAdmission, pytest, inert AST audit.
**Spec:** docs/architecture/TRACKER-STORAGE-BINDING-CONTRACT.md

## Global Constraints

- Source chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9; blob pinned in spec.
- No source threshold change, live imports, disk-backed runtime, downloads or aliases.
- Preserve source JSON/order/refusal semantics; no fabricated historical process IDs.
- No source lock-contention/lifecycle/full-loop/label readiness claim.
- Work in existing dirty feature checkout; no commits, pushes, cleanup or new worktree.
- apply_patch for edits. Reviewer has no nested-agent authority.

## Task 1: Source-faithful causal tracker storage

Create:
- trading_system/tree_replay/_vendor/tracker_storage.py: TrackerStorage(source), load/save.
- trading_system/tree_replay/tracker_storage.py: TrackerStateSeed, StateUnavailable,
  CausalTrackerStorage, private in-memory port backend/quarantine handle.
- trading_system/tree_spec/tracker_storage_source.py: audit_tracker_storage_source(root).
- tools/check_tracker_storage_source_parity.py: --source-root CLI,0verified/2blocked.
- tests/tree_replay/test_tracker_storage.py: actual storage and source consumers.
- tests/tree_spec/test_tracker_storage_source.py: source identity/projection mutation cases.
- docs/architecture/TRACKER-STORAGE-BINDING-USAGE.md: use, effects, limitations.

Consumes existing bars._utc; tracker_admission.TrackerAdmission; read-only pinned
source and existing auditor's _replace_exact/_selected/_dump/_without_doc/_git.
Produces exact public interfaces in spec. No existing runtime/manifest edited.

- [x] Read original _load/_save/_audit_creation and spec. Baseline existing
  tracker tests: `python -m pytest tests/tree_replay/test_tracker_admission.py -q`.
- [x] Write behavioral tests using in-test import lookup (normal collection):
  ```python
  store = storage(status="PRESENT", text='{"z": {}, "a": {}, "b": {}, "c": {}}')
  assert list(store.load()) == ["z", "a", "b", "c"]
  with pytest.raises(RuntimeError, match="would drop 3/4 keys"):
      store.save({"z": {}})
  assert list(store.load()) == ["z", "a", "b", "c"]
  assert store.quarantine_artifacts == {"open_trades.rejected-1788969600": '{\n "z": {}\n}'}
  ```
  Fixture T=2026-09-09T16:00Z, seed observedT-1h/availableT-30m/coveredT+1h.
  Include every test family in spec with literal boundaries, not code-derived oracles.
- [x] Run `python -m pytest tests/tree_replay/test_tracker_storage.py -q --tb=short`
  and observe missing-feature RED before adding runtime.
- [x] Implement private source methods by exact explicit port substitution.
  Preserve source logic, especially creation before shrink rejection and write
  failure before RuntimeError. Source guard delegates is_live_test_target().
  Ports: exists/read_text/audit_creation/quarantine_path/atomic_write/now_epoch.
- [x] Implement seed validation and in-memory ports. Causal guard precedes all
  operations, including allow_shrink saves; do not parse JSON at ingestion.
  ```python
  def load(self):
      if not self.source.exists():
          return {}
      return json.loads(self.source.read_text())
  ```
  Save uses reread current text, never cached initial load. snapshot handoff has
  observed/available=T and retains coverage; generated saves preserve key order.
- [x] Run focused test file GREEN. Exercise real TrackerAdmission record/exposure
  and subsequent same-level selection, retaining unavailable evidence through catches.
- [x] Write source-audit RED mutation tests: correct source must verify; wrong
  commit/blob or changed threshold/reread/extra runtime statement must block.
  Auditor compares whole fixed module/class/imports, not selected runtime methods.
- [x] Implement audit and CLI. Normalize checkout text CRLF for pinned Git blob;
  root must be actual source repo parent. CLI prints readinessfalse even ifverified.
- [x] Run `python -m pytest tests/tree_replay/test_tracker_storage.py tests/tree_spec/test_tracker_storage_source.py tests/tree_replay/test_tracker_admission.py tests/tree_replay/test_admission_frames.py tests/tree_replay/test_state.py -q --tb=short`.
  Verify names exist first; record exact correction if any instead of dropping coverage.
- [x] Run new source parity CLI on retained source parent; inspect whitespace/diffs.
- [x] Self-review, usage/report, task and full component reviews, acceptance record.

## Remaining master work

Bind original lock/caller ordering, quotes/full raw logs, heterogeneous watch state
and generated advisory lifecycle. Complete all producers/simulator/dataset/models
and original human gates. This storage component is not a substitute for those.
