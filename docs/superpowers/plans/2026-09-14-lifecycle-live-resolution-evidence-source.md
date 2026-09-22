# Lifecycle live-resolution evidence implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recover the source live resolver's fresh-price / corrected-bar fallback evidence block as a causal offline prerequisite to its later state-mutation body.

**Architecture:** A private `LifecycleLiveResolutionEvidence(source)` composes the accepted quote-evidence helper with an explicit corrected-bar port and returns only immutable-style evidence values: current prices and forming-bar extremes. A source-pinned AST statement-fragment auditor proves the extracted leading `_check_live_locked` block and all permitted offline adaptations.

**Tech Stack:** Python, pandas, pytest, AST, JSON CLI.

**Spec:** `docs/architecture/LIFECYCLE-LIVE-RESOLUTION-EVIDENCE-SOURCE-INTAKE.md`

## Global constraints

- Pin chart-desk commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9` and tracker blob `b616b34022e436545d8c1daf85eced51614fd74e`; parse/read the retained source, never execute it.
- Reuse `LifecycleLiveEvidence`; do not reimplement or alter its accepted fresh-price semantics.
- Adapt only source state load to a supplied mapping, source corrected-bar fetch to `source.fetch_corrected(symbol, "15m", 2)`, quote file read to `source.quote_payload()`, and wall clocks to `source.now_epoch()`.
- Preserve per-symbol source order, correction rejection, strict timestamp comparison, forming low/high carry-forward and broad per-symbol skip boundary.
- No state mutation, resolver decision, fill, revalidation, outcome, gate/save, delivery, broker/feed access, replay, dataset, economics, model, training or readiness claim. Every audit/report readiness flag stays false.

---

### Task 1: Runtime evidence collector

**Files:**
- Create: `trading_system/tree_replay/_vendor/lifecycle_live_resolution_evidence.py`
- Create: `tests/tree_replay/test_lifecycle_live_resolution_evidence.py`
- Create: `docs/architecture/LIFECYCLE-LIVE-RESOLUTION-EVIDENCE-SOURCE-USAGE.md`

- [x] Start normal RED tests for active-state filtering, `FORCE_BAR_AGE_S` boundary, fallback request identity, correction rejection, exact timestamp winner/loss, range carry-forward, sibling fault isolation and no-state-effect behavior.
- [x] Project the extracted leading `_check_live_locked` evidence statements into a supplied-state collector. It reuses accepted `LifecycleLiveEvidence` for the initial price map, uses only supplied raw quote/clock/corrected-frame ports, and returns prices plus bar extremes without lifecycle transitions.
- [x] Prove with in-memory frames and failure probes that no fallback result can fill, cancel, stop, target, gate, save, emit an outcome/label or establish readiness.
- [x] Run focused tests and obtain independent Task 1 review.

### Task 2: Statement-fragment source audit

**Files:**
- Create: `trading_system/tree_spec/lifecycle_live_resolution_evidence_source.py`
- Create: `tools/check_lifecycle_live_resolution_evidence_source_parity.py`
- Create: `tests/tree_spec/test_lifecycle_live_resolution_evidence_source.py`

- [x] Start normal RED for missing auditor/runtime and mutations of pinned source identity/blob, extracted-statement order, accepted helper identity, active-state filter, fallback call identity, correction guard, timestamp inequality, range/close extraction, exception boundary, CLI serialization and consistency.
- [x] Implement inert AST extraction of only the source statements from the `prices = _live_prices()` setup through the `if not prices: return []` guard; transform only the explicitly allowed offline ports and compare against the runtime projection. The explicit-root JSON CLI fails closed on every error and retains false readiness.
- [x] Run runtime/source focused suites and retained CLI; obtain Task 2 and final combined review.
- [x] On acceptance update usage, tracker, AGENTS and this plan without implying resolver-body, replay/economic/dataset/model completion.

## Explicitly deferred

The source resolver's PENDING and OPEN mutation branches, post-fill window,
ambiguous touch, progress/target/protection/zone logic, outcome writing,
caller gate/save, lock/wrapper, delivery, source acquisition, replay,
dataset, model/evaluation and live gates remain outside this plan.
