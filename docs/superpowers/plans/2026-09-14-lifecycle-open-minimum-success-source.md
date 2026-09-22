# Lifecycle OPEN minimum-success source implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Faithfully project the source's pre-ambiguity OPEN minimum-success
message and raw-fact branch over supplied evidence.

**Architecture:** A private offline resolver composes accepted post-fill
evidence, transition and outcome-shelf helpers but receives all causal facts
from its caller. A static audit pins the physical source fragment and rejects
runtime, child-proof or CLI drift with false readiness.

**Tech Stack:** Python 3, pytest, `ast`, existing private source ports.

**Spec:** `docs/architecture/LIFECYCLE-OPEN-MINIMUM-SUCCESS-SOURCE-INTAKE.md`

## Global Constraints

- Read/parse retained source only; never import or execute it.
- Preserve quote gate and pre-ambiguity ordering exactly.
- Do not acquire data, decide terminal/protective/target state, persist,
  deliver, infer economics or create replay/dataset/training/model behavior.
- Every audit/CLI path retains `ready_for_replay=false` and
  `ready_for_training=false`.

### Task 1: Runtime and focused tests

- [x] TDD `LifecycleOpenMinimumSuccess.resolve(trade, *, low, high, spot,
  quote, has_bar_extremes, minimum_message)` with bar-minimum, quote-minimum,
  stale/wrong-lp/protection gates, short/long directional steps and exactly-one
  raw minimum outcome tests.
- [x] Compose accepted `DeskSuccess`, `LifecycleTransitions` and
  `LifecycleOutcomeShelf`; use only the offline source clock.
- [x] Add a usage document that makes the supplied-evidence and non-economic
  boundary explicit; run focused tests and independent task review.

### Task 2: Source audit and final acceptance

- [x] TDD a fail-closed auditor/explicit-root CLI for physical lines 2690–2704,
  required accepted child proofs and runtime AST projection.
- [x] Cover source identity/order, quote/protection/minimum mutations, malformed
  child/audit/JSON reports and missing root; retain false readiness.
- [x] Run combined tests/CLI, independent task/final reviews and Codex
  acceptance before composing this branch into a resolver.
