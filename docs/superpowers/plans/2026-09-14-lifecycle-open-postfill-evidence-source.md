# Lifecycle OPEN post-fill evidence implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans task-by-task.

**Goal:** Faithfully recover only the source's safe post-fill price-window evidence for an OPEN record.

**Architecture:** A private offline collector composes accepted live evidence,
bar lifecycle primitives and DeskSuccess. It accepts one supplied OPEN record
and spot/corrected-tape ports, returns only `(low, high, minimum_message)`.

**Spec:** `docs/architecture/LIFECYCLE-OPEN-POSTFILL-EVIDENCE-SOURCE-INTAKE.md`

## Constraints

- Pin and parse the retained source only; never execute/import it.
- Preserve correction gates, fill location, fill-bar convention, broad tape
  failure fallback, and spot inclusion exactly.
- No resolver mutation, terminal result, outcome, persistence/gate/delivery,
  economics/replay/dataset/model work or readiness claim.

### Task 1: Runtime collector

- [x] Create runtime, focused TDD tests and usage documentation for supplied
  post-fill windows, including unsafe/unlocatable/failing-tape spot fallback.
- [x] Compose accepted helpers without duplicating their policy; return raw
  evidence only.
- [x] Run focused tests and independent review.

### Task 2: Source audit

- [x] Create a fail-closed AST auditor, explicit-root CLI and mutation tests.
- [x] Verify source identity, exact projection and accepted child proofs while
  retaining false replay/training readiness.
- [x] Run combined tests/CLI, final review and acceptance documentation.
