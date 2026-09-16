# Full-Tree Historical Evidence Capture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an offline recording boundary that converts caller-supplied,
point-in-time full-tree inputs into replayable scheduled evidence bundles.

**Architecture:** A typed supplied-input port returns private values with an
availability window and source-adapter digest. A recording source implements the
same 13 ports used by the existing full-tree provider, invokes the actual tree
only to discover source calls, and turns each observed call into an immutable
artifact/operation. The existing replay reruns the resulting bundle; capture
does not expose a source `Walk`, `Plan` or result.

**Tech Stack:** Python 3, dataclasses, pandas, existing full-tree contracts,
pytest.

**Spec:** `docs/superpowers/specs/2026-09-15-full-tree-evidence-capture-design.md`

## Global Constraints

- No filesystem, network, vendor client, data download or raw-data persistence.
- Accept only caller-supplied values with explicit UTC availability windows and
  SHA-256 digests.
- Support only `full_tree:house`, `full_tree:strict`, `TREE_WALK` and
  `TREE_REVALIDATION`.
- Run actual local `TreeReader` / `TreeRevalidation`; accept no final result
  injection.
- Keep all raw values and private pending plans out of manifests, receipts,
  checkpoints and agent-exchange.
- Do not create economics, labels, datasets, models or live-trading behavior.

---

## File Structure

| File | Responsibility |
| --- | --- |
| `trading_system/tree_replay/full_tree_capture.py` | Supplied capture-value contract, recording port source, capture runner and receipt. |
| `tests/tree_replay/test_full_tree_capture.py` | Contract, ordering, availability, source-error and replay-equivalence tests. |
| `docs/architecture/FULL-TREE-EVIDENCE-CAPTURE-USAGE.md` | Explicit offline usage boundary and handoff requirements for a later data adapter. |
| `tools/check_full_tree_capture_source.py` | Static guard against live imports/final-result injection in capture code. |
| `tests/tree_spec/test_full_tree_capture_source.py` | Static-audit regression tests. |

### Task 1: Supplied-value contracts and recorder core

**Files:**
- Create: `trading_system/tree_replay/full_tree_capture.py`
- Create: `tests/tree_replay/test_full_tree_capture.py`

**Interfaces:**
- `CapturedValue(value, observed_at, available_at, covered_through, content_digest)`
- `FullTreeCaptureInput.read(kind, arguments, *, decision_time) -> CapturedValue`
- `FullTreeEvidenceCapture.capture_walk(...) -> FullTreeCaptureResult`
- `FullTreeCaptureResult.bundle` and payload-free `receipt`.

- [ ] **Step 1: Write failing tests** for one frame capture, one clock capture,
  exact argument forwarding and a result whose public receipt omits raw values.
- [ ] **Step 2: Run the narrow test file in red.**

  Run: `python -B -m pytest tests/tree_replay/test_full_tree_capture.py -q --tb=short -p no:cacheprovider`

  Expected: FAIL because capture classes do not exist.

- [ ] **Step 3: Implement minimal typed contracts and a recording port source.**
  Validate timestamps/digest shape via existing full-tree contracts. Every port
  must call the supplied input once with canonical arguments and append one
  distinct artifact/operation; no cache or dedupe.
- [ ] **Step 4: Run Task 1 tests green** and add missing/late/wrong-kind cases.
- [ ] **Step 5: Commit.**

  ```bash
  git add trading_system/tree_replay/full_tree_capture.py tests/tree_replay/test_full_tree_capture.py
  git commit -m "feat: capture supplied full-tree evidence"
  ```

### Task 2: Actual tree and revalidation capture paths

**Files:**
- Modify: `trading_system/tree_replay/full_tree_capture.py`
- Modify: `tests/tree_replay/test_full_tree_capture.py`

**Interfaces:**
- Capture invokes `TreeReader(recording_source).walk(...)` and conditionally
  `trade_from_walk(...)`; it discards the final object.
- Revalidation capture invokes `TreeRevalidation(recording_source)` only with a
  private, digest-committed pending plan.

- [ ] **Step 1: Write red tests** using literal supplied multiframe evidence.
  Cover house/strict captures, repeated fetches, source-caught `ERROR`, an early
  source stop, revalidation at the two-hour boundary and shadow write ordering.
- [ ] **Step 2: Run them in red.**
- [ ] **Step 3: Implement actual source execution.** Create a `FullTreePass`
  only from recorded calls, never from a caller-provided final result. Ensure
  `assert_no_unexpected_calls` verifies all recorded calls and a stopped path
  commits only reached operations.
- [ ] **Step 4: Verify output by rerunning each bundle through
  `FullTreeCausalReplay`;** compare payload-free trace digest with the capture
  receipt, not raw source output.
- [ ] **Step 5: Commit.**

  ```bash
  git add trading_system/tree_replay/full_tree_capture.py tests/tree_replay/test_full_tree_capture.py
  git commit -m "feat: record actual full-tree evidence schedules"
  ```

### Task 3: Static guard, usage contract and review

**Files:**
- Create: `tools/check_full_tree_capture_source.py`
- Create: `tests/tree_spec/test_full_tree_capture_source.py`
- Create: `docs/architecture/FULL-TREE-EVIDENCE-CAPTURE-USAGE.md`
- Create: agent-exchange review requests and acceptance/revision status records.

- [ ] **Step 1: Write red static-audit tests** that mutate a live-loader import
  and a capture method accepting `walk`/`plan`/`result` input.
- [ ] **Step 2: Implement source-text audit** requiring only the supplied input,
  existing reader/revalidation bindings, false readiness claims and no known
  live-loader modules.
- [ ] **Step 3: Write usage documentation** stating required future adapter
  responsibilities: exact source identity, raw digest semantics, availability,
  missing-data treatment and private retention.
- [ ] **Step 4: Run combined regression.**

  ```powershell
  python -B -m pytest tests/tree_replay/test_full_tree_capture.py tests/tree_replay/test_full_tree_contracts.py tests/tree_replay/test_full_tree_provider.py tests/tree_replay/test_full_tree_replay.py tests/tree_replay/test_full_tree_checkpoint.py tests/tree_replay/test_tree_walk.py tests/tree_replay/test_tree_revalidation.py tests/tree_spec/test_full_tree_capture_source.py tests/tree_spec/test_full_tree_replay_source.py -q --tb=short -p no:cacheprovider
  python -B tools/check_full_tree_capture_source.py
  python -B tools/check_full_tree_replay_source_parity.py --source-root C:\Users\roeea\AppData\Local\Temp\tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
  ```

- [ ] **Step 5: Request two independent read-only reviews.** Acceptance must
  state test counts, commits, scope and that no external data/economic/model/
  live capability was authorized.
