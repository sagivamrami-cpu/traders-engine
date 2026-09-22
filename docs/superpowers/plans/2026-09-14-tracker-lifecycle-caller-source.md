# Tracker lifecycle caller source implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement and independently prove the changed-only tracker caller
seam that persists lifecycle gating before state save in closed-bar and
lock-protected live passes.

**Architecture:** A small `TrackerLifecycleCaller(source)` composes accepted
`LifecycleGate` with the source context's shared `TrackerLock` policy; unported
source mutation kernels provide only raw state mutation and `(out, changed)`.
A separate inert auditor pins the source tail/wrapper and invokes actual child
audits.

**Tech Stack:** Python, pytest, AST, JSON CLI.

**Spec:** `docs/architecture/TRACKER-LIFECYCLE-CALLER-SOURCE-CONTRACT.md`

## Global constraints

- Pin chart-desk commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`, tracker
  blob `b616b34022e436545d8c1daf85eced51614fd74e`.
- Parse/read retained source only. Do not import it or call network, broker,
  filesystem, queue or transport services.
- This seam is not the full bar/live resolver. Do not invent thresholds or use
  pre-decided gate, save, receipt or delivery data.
- Every success report continues to say replay/training false.

---

### Task 1: Changed-only runtime caller seam

**Files:**
- Create: `trading_system/tree_replay/lifecycle_caller.py`
- Create: `tests/tree_replay/test_lifecycle_caller.py`
- Modify: `docs/architecture/TRACKER-LIFECYCLE-CALLER-SOURCE-CONTRACT.md`

- [x] Write normal RED against a missing runtime with one raw tape supplying
  real accepted lifecycle gate, storage and lock effects.
- [x] Prove closed pass: single load; empty returns before resolver/gate/save;
  unchanged returns raw output with no gate/save; changed is resolver → gate →
  save, with exact output/order.
- [x] Prove malformed callback output fails before gate/save and non-LockBusy
  resolver/lock errors propagate without fake success.
- [x] Prove live lock has `skip_if_busy=True`, returns empty without effects
  on LockBusy, and changed order is lock → load → resolve → gate → save →
  release.
- [x] Implement minimally; run focused runtime plus actual lifecycle-gate,
  tracker-lock/storage consumers. Get independent task review and close all
  findings before Task 1 acceptance.

### Task 2: Source-tail audit

**Files:**
- Create: `trading_system/tree_spec/tracker_lifecycle_caller_source.py`
- Create: `tools/check_tracker_lifecycle_caller_source_parity.py`
- Create: `tests/tree_spec/test_tracker_lifecycle_caller_source.py`

- [x] Write normal RED for absent auditor/runtime and mutations of baseline,
  commit/blob, selected source tail/order, LockBusy boundary, runtime
  constructor/interface/AST, child failure/exception/report shape.
- [x] Implement inert AST/text proof plus explicit-root JSON CLI. Invoke actual
  lifecycle-gate and tracker-lock auditors and fail closed for every error.
- [x] Run focused runtime/source/child suites and retained CLI; obtain task
  review then a separate combined final review.
- [x] On acceptance update usage, tracker, AGENTS and this plan; preserve all
  unresolved resolver/replay/economic/model work.

## Explicitly deferred

Source mutation bodies, parked replay caller context, delivery, market-watch
arbitration/watch state, full causal scheduler/checkpoint, remaining producers,
simulation, historical labels/dataset, model training/evaluation and every
live/promotion decision are outside this plan.
