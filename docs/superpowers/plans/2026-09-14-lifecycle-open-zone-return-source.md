# Lifecycle OPEN zone-return source implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Faithfully project the live OPEN zone-return notification state
machine without turning its recheck label into a lifecycle decision.

**Architecture:** A private supplied-spot resolver composes accepted entry-band,
lifecycle-transition/voice, DeskSuccess and Revalidation components. An AST
auditor pins the helper source fragment and rejects runtime/child/CLI drift.

**Tech Stack:** Python 3, pytest, ast, existing private tree-replay ports.

**Spec:** `docs/architecture/LIFECYCLE-OPEN-ZONE-RETURN-SOURCE-INTAKE.md`

## Global Constraints

- Read/parse retained source only; never import or execute it.
- Preserve single-message-per-excursion and target-only rearm behavior.
- Retain the actual `Revalidation(source).still_valid` child call. The recheck
  is a label, never a veto, terminal mutation or raw outcome.
- `spot` is supplied, but the inherited revalidation child may fetch corrected
  evidence or attempt source-owned shadow writes through its offline ports; do
  not replace it with a precomputed-label port or claim this composition cannot
  acquire/revalidate.
- Do not add direct zone-return persistence/delivery/economic behavior or
  replay/dataset/training/model behavior; readiness stays false.

### Task 1: Runtime source projection

- [x] TDD a `LifecycleOpenZoneReturn(source).resolve(trade, *, spot)` private
  component for long/short entry-band touch, no-excursion, repeated suppression,
  target-only rearm, malformed marker, source journey and all three recheck
  labels including caught error.
- [x] Use accepted helpers; prove the real revalidation child boundary is
  invoked through supplied offline ports, it mutates only `zone_return_at` when
  a message is emitted, and zone-return itself writes no
  terminal/outcome/persistence effect.
- [x] Add usage boundary and independent task review.

### Task 2: Static proof and acceptance

- [x] TDD AST auditor/explicit-root CLI for helper source lines 1046–1106 and
  live-call boundary 2751–2759, with exact child proof requirements.
- [x] Test source/range/rearm/recheck/message-order mutations, source identity,
  malformed children and fail-closed CLI JSON paths with false readiness.
- [x] Run combined tests/CLI, task/final reviews and Codex acceptance.
