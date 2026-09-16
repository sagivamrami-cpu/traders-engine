# Lifecycle outcome and shelf source implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recover the tracker’s outcome-event append, expiry policy and shelf-write helpers as an offline, source-pinned resolver prerequisite.

**Architecture:** `LifecycleOutcomeShelf(source)` projects the selected helper set as instance methods over logical artifacts and accepted atomic source ports. It imports the accepted `TrackerAdmission` only for `has_open`; a separate AST auditor pins source, full projection and actual child proof.

**Tech Stack:** Python, pytest, AST, JSON CLI.

**Spec:** `docs/architecture/LIFECYCLE-OUTCOME-SHELF-SOURCE-INTAKE.md`

## Global constraints

- Pin chart-desk commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9` and tracker blob `b616b34022e436545d8c1daf85eced51614fd74e`.
- Read/parse retained source only; never import it, touch host artifacts, access a feed/broker, deliver a message or claim an economic result.
- Preserve selected source order, text, constants, exception boundaries and state/effect ordering. Only source wall clocks become `source.now_epoch()`.
- Event records are tracker facts, never labels. All tests/audits keep replay/training readiness false.

---

### Task 1: Outcome/shelf helper runtime

**Files:**
- Create: `trading_system/tree_replay/_vendor/lifecycle_outcome_shelf.py`
- Create: `tests/tree_replay/test_lifecycle_outcome_shelf.py`
- Create: `docs/architecture/LIFECYCLE-OUTCOME-SHELF-SOURCE-USAGE.md`

- [x] Start with normal missing-module RED tests for source ordering of clock,
  outcome payload and append, expiry priority, shelf lineage, malformed shelf
  fallback, atomic cleanup/propagation and actual accepted `has_open` behavior.
- [x] Project the complete selected source set in exact order. Adapt only
  logical artifact/clock/atomic I/O expressions to supplied offline ports;
  preserve `event_ts` truthiness and source error boundaries.
- [x] Prove no helper creates a label, reads a market feed, delivers a message,
  returns a fill/economic assertion or establishes replay/training readiness.
- [x] Run focused tests against real tracker-admission and lifecycle-gate
  dependency implementations; obtain independent Task 1 review and close
  findings.

### Task 2: Source audit

**Files:**
- Create: `trading_system/tree_spec/lifecycle_outcome_shelf_source.py`
- Create: `tools/check_lifecycle_outcome_shelf_source_parity.py`
- Create: `tests/tree_spec/test_lifecycle_outcome_shelf_source.py`

- [x] Start normal RED for missing auditor/runtime and mutations of source
  identity/blob, selected order/signatures/constants, clock/I/O substitutions,
  child identity/projections, malformed child reports and CLI serialization.
- [x] Implement an inert full AST projection and explicit-root JSON CLI.
  Require actual tracker-admission and lifecycle-gate child audits; pin child
  identities/projections immutably and fail closed on every source/child/CLI
  error.
- [x] Run focused runtime/source/child suites and retained CLI; obtain Task 2
  review then independent combined final review.
- [x] On acceptance update usage, tracker, AGENTS and this plan without
  implying resolver-loop, economic-label, replay/dataset/model completion.

## Explicitly deferred

Shelf revival/reads, outcome reconciliation, resolver loops, causal bars/quotes,
revalidation/gate/save composition, execution/fills/economics, replay, dataset,
model/evaluation and live gates remain outside this plan.
