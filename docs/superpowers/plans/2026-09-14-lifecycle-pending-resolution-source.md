# Lifecycle PENDING-resolution source implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Project the pinned live resolver's PENDING fill/cancel decision slice over supplied offline evidence, without advancing an OPEN trade.

**Architecture:** `LifecyclePendingResolution(source)` will compose accepted
entry-band, outcome-shelf, lifecycle-transition and tree-revalidation
components. It accepts a single already-selected pending record, a supplied
state image, and supplied price/extreme evidence; it returns source-style
messages plus a changed flag. A separate AST projection auditor will pin the
exact source branch and every permitted offline adaptation.

**Tech Stack:** Python, pytest, pandas fixtures, AST, JSON CLI.

**Spec:** `docs/architecture/LIFECYCLE-PENDING-RESOLUTION-SOURCE-INTAKE.md`

## Global constraints

- Read/parse only the retained chart-desk source at commit
  `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`, tracker blob
  `b616b34022e436545d8c1daf85eced51614fd74e`; never import or execute it.
- Preserve source branch order, touch inequalities, raw outcome timing,
  source field names, and one-clock fill timestamp assignment.
- Reuse accepted `LifecycleOutcomeShelf`, `LifecycleTransitions`,
  `TreeRevalidation`, and entry-band helper. No duplicated policy.
- Do not load/save, lock, gate/deliver, acquire quotes/bars, invoke the OPEN
  branch, calculate economics, create labels/dataset rows, fit/evaluate a
  model, or claim replay/training readiness. Every audit report keeps both
  readiness flags false.

---

### Task 1: PENDING resolution runtime

**Files:**
- Create: `trading_system/tree_replay/_vendor/lifecycle_pending_resolution.py`
- Create: `tests/tree_replay/test_lifecycle_pending_resolution.py`
- Create: `docs/architecture/LIFECYCLE-PENDING-RESOLUTION-SOURCE-USAGE.md`

**Interfaces:**
- Consumes: `resolve(trade, *, state, price, bar_extremes)` where `trade` is a
  supplied mutable record and `bar_extremes` maps symbols to `(low, high)`.
- Produces: `(messages: list[tuple[str, bool]], changed: bool)`; raw outcome
  writes only on the two source cancellation branches.

- [x] Write normal RED tests for long/short one-sided touches, absent-extreme
  spot fallback, no-touch immutability, open-slot cancellation, failed
  revalidation cancellation, successful verified/unverified fill, exact
  fields/clock sharing/message order, no fill outcome, and no load/save/gate/
  quote/bar/open-branch effect.
- [x] Implement the smallest source-projected resolver that composes accepted
  helpers and uses only supplied inputs/explicit raw artifact ports.
- [x] Run the focused runtime suite and request an independent Task 1 review.

### Task 2: PENDING branch source audit

**Files:**
- Create: `trading_system/tree_spec/lifecycle_pending_resolution_source.py`
- Create: `tools/check_lifecycle_pending_resolution_source_parity.py`
- Create: `tests/tree_spec/test_lifecycle_pending_resolution_source.py`

**Interfaces:**
- Consumes: retained `tracker.py` and the Task 1 runtime source text.
- Produces: fail-closed JSON source-parity report that includes child proof
  results and always reports false replay/training readiness.

- [ ] Write normal RED tests for missing runtime/auditor, source commit/blob,
  branch extraction/order, every adapted call, touch inequalities, conflict/
  failed/successful outcome paths, timestamp assignment, dependency drift and
  malformed CLI/audit serialization.
- [ ] Implement AST extraction of exactly the source PENDING branch and an
  explicit offline projection; verify the real runtime and accepted child
  auditors without executing original source.
- [ ] Run combined runtime/source suites and the retained-source CLI; obtain
  independent audit and final reviews.
- [ ] On acceptance update usage, tracker, AGENTS, ledger and this plan without
  implying full resolver, replay, economics, dataset or model completion.

## Explicitly deferred

The outer loop, same-pass OPEN progression, all OPEN protection/progress/
target/stop logic, state persistence/gate composition, real historical
availability, economic outcomes, dataset labels, model fitting/evaluation,
promotion and live trading remain outside this plan.
