# Admission dependencies implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Track steps with checkboxes.

**Goal:** Supply original admission calculations and a causal evidence store for
the next outer producer gate adapter; not declare the whole replay complete.

**Architecture:** Pure pinned source projections, independently audited, alongside
an immutable publication-time memory journal. Keep source advisory evidence
separate from future economic execution state.

**Tech Stack:** Python, pandas/numpy, dataclasses, hashlib/json, pytest, AST/git audits.

**Spec:** docs/architecture/ADMISSION-DEPENDENCIES-CONTRACT.md

## Global Constraints

- Preserve chart-desk 68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9 and trading-floor d827dd792cbd1d396b4ee325879c63e57388e07a.
- No live source imports, network/feed/state reads, notifications, broker calls, datasets or training.
- No source instrument alias; shadow quality is not a veto; source advisory state is not economic state.
- Public replay_ready/training_ready/tradeable remain false.
- Preserve the existing dirty in-place branch; no commits, pushes, worktree creation or cleanup.
- All file edits use apply_patch. Tests use synthetic data. Source parity reads retained source only.
- New files only in each task's scoped paths; parent owns master/ledger/status acceptance.

## Task 1: Original admission calculation closure

**Files:** Create `_vendor/admission_matrix.py`, `_vendor/admission_toolkit.py`,
`_vendor/admission_indicators.py` as needed, `_vendor/admission_quality.py`,
`_vendor/admission_clocks.py`, `_vendor/admission_swing.py` under
`trading_system/tree_replay/`; `trading_system/tree_spec/admission_source.py`;
`configs/trees/admission-source-contracts.json`; `tools/check_admission_source_parity.py`;
`tests/tree_replay/test_admission_calculations.py`,
`tests/tree_spec/test_admission_source.py`; `docs/architecture/ADMISSION-CALCULATIONS-USAGE.md`.

**Consumes:** Pinned source chartdesk/{matrix,toolkit,indicators,tr,entry_quality,windows,zones}.py
and floor/marketclock.py. Retained root:
`C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`.
Inspect existing vendor tr/indicators and audit modules before reuse; no modifications
to previous accepted source modules/manifests. Add own dependency projection if needed.

**Produces:** `admission_matrix.read_frame(df, tf, basis_note=None) -> TFView`,
original matrix tool functions/types/constants, `admission_quality.evaluate(...)`
and helpers with source signatures, `admission_swing._last_swing(df, up)`,
`admission_clocks.outside_reason(now)` / `entry_blocked(now)` with required aware time,
and `audit_admission_source(source_root) -> dict` with source_subset_verified,
blockers and false readiness. CLI accepts `--source-root` explicit parent root.

- [ ] Write failing calculation/clock/quality/swing and source-audit tests.
  Example boundary expectation (UTC equivalent of Monday Jerusalem 02:00):

  ```python
  from datetime import datetime
  from zoneinfo import ZoneInfo
  def test_hunting_starts_at_two():
      t = datetime(2026, 9, 7, 2, tzinfo=ZoneInfo('Asia/Jerusalem'))
      assert clocks.outside_reason(t) is None
      assert clocks.outside_reason(t.replace(hour=1, minute=59)) is not None
  ```

  Test exact 21:00 exclusion; Friday 21:30 preclose; Friday23/Sunday/Monday01;
  timezone-equivalent instants and DST, naive/missing time rejection. Golden matrix
  read outputs for synthetic rising/falling/mixed prices; source zero-volume VWAP
  fallback and NaN behavior. Quality named anchors vs shadow flag without veto.
  Swing needs three bars to the right. Audit mutations must independently corrupt
  a constant, function, order, dependency alias and clock specialization.
- [ ] Run `python -m pytest tests/tree_replay/test_admission_calculations.py tests/tree_spec/test_admission_source.py -q --tb=short`; record RED.
- [x] Port only full required source definitions, preserving their AST except
  declared import/clock/fetch specialization. For read_frame, copy TFView constructor
  expression from read_tf, using its supplied df/tf/basis_note. Audit the expression
  against source rather than merely asserting that the new function exists.
  Pin complete ordered dependency closure and blobs. Do not execute live source.
- [x] Run the same suite GREEN and the explicit-root source CLI; document edge
  behavior and scope. Self-review imports and no hidden source access.
- [x] Write exchange result; parent generates task diff, independent spec/quality
  review, re-verifies and records acceptance before dependent binding work.

## Task 2: Causal source-advisory memory evidence

**Files:** Create `trading_system/tree_replay/state.py`,
`tests/tree_replay/test_state.py`, `docs/architecture/CAUSAL-ADMISSION-MEMORY-USAGE.md`.

**Consumes:** stdlib; existing timestamp helper may be reused after inspecting its
contract. No Task1 runtime dependencies, so local work can proceed alongside Task1.
**Produces:** frozen kw-only `MemoryEvent`, `MemoryJournal`,
`memory_asof(journal, decision_time) -> dict`, `checkpoint_memory(journal) -> dict`,
`restore_memory(checkpoint) -> MemoryJournal`, exact fields/schema in spec.

- [x] Write failing tests. Representative fixture/assertion:

  ```python
  event = MemoryEvent(event_id='e1', sequence=1, stream='tracker', key='trade1',
      observed_at=t, available_at=t, payload_json='{"state":"PENDING"}')
  journal = MemoryJournal(journal_id='j1', origin='supplied_source_advisory',
      start_at=t, covered_through=t, complete=True, events=(event,))
  result = memory_asof(journal, t)
  assert result['tracker_state']['trade1']['state'] == 'PENDING'
  assert result['replay_ready'] is False
  assert restore_memory(checkpoint_memory(journal)) == journal
  ```

  Cover delayed/future revisions, tied time ordered by sequence, incomplete/empty,
  start/end coverage boundary, missing-state row retention, forged future ts/resolved_ts,
  duplicate IDs/sequences/JSON keys, native type rejection, invalid streams/origin,
  invalid JSON/nonfinite/nested payload, detached output and checkpoint tampering.
- [x] Run `python -m pytest tests/tree_replay/test_state.py -q --tb=short`; record RED.
- [x] Implement strict construction/validation and reduction. Decode JSON with
  duplicate-key rejection and finite numbers, normalize with sorted compact JSON.
  Select by actual publication time, never use final-state snapshots for earlier T.
  The hash input is the visible report excluding evaluation_hash itself; checkpoint
  checksum covers schema and entire canonical journal. Restore goes through normal
  constructors and fails on extra/missing fields, bad checksum or schema.
- [x] Run GREEN, document usage/limitations, independently review and accept.

## Combined acceptance

Current status: component accepted125556Z-codex-admission-dependencies after both
task reviews, combined review and scoped identity fix review. Task1 original
worker RED history remains unavailable (its two unchecked history steps above
are evidence gaps, not runtime work to fabricate). Temporal/test/identity findings
closed. Test-root portability remains deferred before another runner/CI.

- [x] Run both new suites plus producer/frame/correction/state-adjacent suites.
- [x] Run source CLI and independent combined review of this component's full diff.
- [x] Record exact counts/commands; update tracker/memory without closing C/E/F.
- [x] Continue next into original tracker gate closure and real producer binding,
  including rejection-log selection, OPEN vs PENDING, post-stop calculation inputs,
  same-level and episode gates. This plan does not substitute supplied booleans
  for executing those gates or claim lifecycle transitions were reconstructed.
  Continuation started in2026-09-09-tracker-admission-source.md; this checkbox
  records handoff only, not completion of that source closure or public binding.
