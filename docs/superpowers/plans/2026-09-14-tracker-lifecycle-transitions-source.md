# Tracker lifecycle transitions source implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recover the source lifecycle transition/message helpers consumed by
both tracker resolver paths, using accepted offline clocks and dependencies.

**Architecture:** `LifecycleTransitions(source)` is a private projection of the
selected tracker helper set. It owns one `DeskSuccess(source)` for stop-note
state and uses accepted voice, symbols and entry-band geometry. A separate
static auditor compares a full AST projection and actual child audits.

**Tech Stack:** Python, pytest, AST, JSON CLI.

**Spec:** `docs/architecture/TRACKER-LIFECYCLE-TRANSITIONS-SOURCE-INTAKE.md`

## Global constraints

- Pin chart-desk commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9` and tracker
  blob `b616b34022e436545d8c1daf85eced51614fd74e`.
- Read/parse source only. Never import retained source, access a live feed,
  send a message, write outcomes, call a broker or make model/dataset claims.
- Preserve source helper ordering, literal text, exception boundaries and state
  mutations. Only source wall-clock terminal stamps become `source.now_epoch()`.
- All tests and audits retain replay/training readiness false.

---

### Task 1: Transition helper runtime

**Files:**
- Create: `trading_system/tree_replay/_vendor/lifecycle_transitions.py`
- Create: `tests/tree_replay/test_lifecycle_transitions.py`
- Create: `docs/architecture/TRACKER-LIFECYCLE-TRANSITIONS-SOURCE-USAGE.md`

- [x] Start with a normal missing-module RED suite over raw source clocks and
  accepted voice/success/entry-band dependencies; no pre-decided outputs.
- [x] Project every selected helper in source order into `LifecycleTransitions`.
  Prove source message text/format paths, progress cap/continuation, published
  stop behavior, all ambiguity/protective result categories and exact terminal
  clock mutation.
- [x] Prove malformed trade fields/clock failure retain source exception or
  fallback boundaries; no helper may persist, journal, deliver or claim fill/
  economic success.
- [x] Run focused tests with actual lifecycle-bars, voice and desk-success
  consumers. Obtain independent Task 1 review and close findings.

### Task 2: Source audit

**Files:**
- Create: `trading_system/tree_spec/lifecycle_transitions_source.py`
- Create: `tools/check_lifecycle_transitions_source_parity.py`
- Create: `tests/tree_spec/test_lifecycle_transitions_source.py`

- [x] Start normal RED for missing auditor/runtime and mutations of identity,
  selected order/signatures/constants/text substitutions, terminal clock,
  internal binding and all child-audit failures/identity drift.
- [x] Implement inert full AST projection plus explicit-root JSON CLI, invoking
  actual lifecycle-primitives, lifecycle-bars and desk-success dependency
  audits. Fail closed on every source/child/CLI error.
- [x] Run focused runtime/source/child suites and retained CLI; obtain Task 2
  review then independent combined final review.
- [x] On acceptance update usage, tracker, AGENTS and this plan without
  implying resolver-loop, replay/economic/dataset/model completion.

## Explicitly deferred

The actual closed-bar/live resolver loops, raw feed causality, revalidation,
outcomes/shelf effects, parked replay context, delivery, scheduler/checkpoint,
all remaining producers, simulation, historical dataset and all model/eval/live
gates remain outside this plan.
