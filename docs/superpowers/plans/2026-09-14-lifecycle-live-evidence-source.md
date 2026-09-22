# Lifecycle live-evidence source implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recover the tracker’s quote-freshness and post-fill historical-replay evidence helpers as an offline, source-pinned prerequisite to the live resolver.

**Architecture:** `LifecycleLiveEvidence(source)` is a private projection of the four selected tracker facts. It receives raw quote payload/operation clock and in-memory bar data; a static AST auditor pins the source projection and every permitted adaptation.

**Tech Stack:** Python, pandas, pytest, AST, JSON CLI.

**Spec:** `docs/architecture/LIFECYCLE-LIVE-EVIDENCE-SOURCE-INTAKE.md`

## Global constraints

- Pin chart-desk commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9` and tracker blob `b616b34022e436545d8c1daf85eced51614fd74e`.
- Read/parse retained source only. Never fetch live/historical data, touch a broker, send/deliver a message, mutate a trade, emit an outcome or make dataset/model claims.
- Preserve selected source order, constants, exception boundaries and per-row handling. Only source quote-file/time expressions become explicit raw payload/operation-clock ports.
- All tests/audits retain replay/training readiness false.

---

### Task 1: Live-evidence runtime

**Files:**
- Create: `trading_system/tree_replay/_vendor/lifecycle_live_evidence.py`
- Create: `tests/tree_replay/test_lifecycle_live_evidence.py`
- Create: `docs/architecture/LIFECYCLE-LIVE-EVIDENCE-SOURCE-USAGE.md`

- [x] Start with normal missing-module RED tests for exact quote age boundaries,
  non-finite/malformed sibling isolation, raw operation clock use, OPEN-only
  replay safety, correction/timestamp rejection and no-state-effect behavior.
- [x] Project the full selected source set in physical order and adapt only
  quote-file read plus wall clock to `source.quote_payload()` and
  `source.now_epoch()`.
- [x] Prove historical replay safety is evidence-only: it cannot make a stale
  quote fresh, fill PENDING, choose an entry/target/stop or create any label.
- [x] Run focused tests against pandas inputs and obtain independent Task 1
  review.

### Task 2: Source audit

**Files:**
- Create: `trading_system/tree_spec/lifecycle_live_evidence_source.py`
- Create: `tools/check_lifecycle_live_evidence_source_parity.py`
- Create: `tests/tree_spec/test_lifecycle_live_evidence_source.py`

- [x] Start normal RED for missing auditor/runtime and mutations of source
  identity/blob, physical order/signatures/constants, payload/clock
  substitutions, error boundaries and CLI serialization/consistency.
- [x] Implement inert full AST projection plus explicit-root JSON CLI. Fail
  closed on every source/audit/CLI error and require false readiness.
- [x] Run focused runtime/source suites and retained CLI; obtain Task 2 and
  independent combined final review.
- [x] On acceptance update usage, tracker, AGENTS and this plan without
  implying live resolver/replay/economic/dataset/model completion.

## Explicitly deferred

Corrected-bar acquisition/fallback, fill/extremes, resolver state changes,
transition outcomes, revalidation/gate/save, delivery, execution/economics,
replay, dataset, model/evaluation and live gates remain outside this plan.
