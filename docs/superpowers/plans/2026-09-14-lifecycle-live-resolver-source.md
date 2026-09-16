# Lifecycle live resolver source implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Faithfully compose the pinned live PENDING/OPEN resolution kernel
over explicit offline ports, preserving source observation and branch order.

**Architecture:** A new private resolver owns a three-part source observation
snapshot `(prices, bar_extremes, raw_quotes)` because the previously accepted
two-part evidence component cannot provide the source `_q` snapshot without a
non-source third quote read. It then composes accepted PENDING, post-fill,
minimum-success, ambiguity, ordinary and zone-return components on the same
mutable state records. A read-only AST auditor pins the complete source kernel
and the exact composition/adaptation boundary.

**Tech Stack:** Python 3, pytest, ast, JSON CLI, existing private tree-replay
ports.

**Spec:** `docs/architecture/LIFECYCLE-LIVE-RESOLVER-SOURCE-INTAKE.md`

## Global Constraints

- Read/parse retained source only; never import or execute it.
- Pin chart-desk commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9` and tracker
  blob `b616b34022e436545d8c1daf85eced51614fd74e`.
- Preserve exactly two source quote observations: `_live_prices()` then the
  raw `_q` snapshot. Do not use a third `quote_payload()` call in composition.
- Preserve `list(state.items())`, terminal/price skips, PENDING same-pass OPEN
  fall-through, ambiguity `continue`, and zone return only after OPEN remains
  nonterminal.
- Reuse accepted lifecycle child components; do not duplicate their decision
  policies. The narrow accepted two-part evidence component remains unchanged.
- No load/save/lock/gate/delivery/broker execution/economic/replay/dataset/
  training/model behavior; all readiness stays false.

### Task 1: Source-ordered runtime kernel

**Files:**
- Create: `trading_system/tree_replay/_vendor/lifecycle_live_resolver.py`
- Create: `tests/tree_replay/test_lifecycle_live_resolver.py`
- Create: `docs/architecture/LIFECYCLE-LIVE-RESOLVER-SOURCE-USAGE.md`

**Interfaces:**
- Consumes: `LifecycleLiveResolver(source).resolve(state: dict)` where `state`
  is a supplied mutable tracker mapping and `source` supplies only the accepted
  offline quote/bar/revalidation/outcome ports.
- Produces: `(messages: list[tuple[str, bool]], changed: bool)`; child
  components own all permitted raw outcome or trade mutations.

- [x] Write failing tests for exactly two quote observations, raw quote
  forwarding to minimum success, terminal/no-price/no-price-map skips, forming
  bar fallback, PENDING no-touch/cancellation/successful same-pass OPEN, and
  one mutable-state record per selected source item.
- [x] Add failing ordering tests that prove minimum precedes ambiguity, an
  ambiguity causes `continue`, ordinary receives the actual minimum message,
  ordinary terminal handling prevents zone return, and unchanged OPEN reaches
  zone return after ordinary processing.
- [x] Implement only `LifecycleLiveResolver` and its private source-observation
  helper; use accepted child classes rather than copied policy.
- [x] Run the focused runtime suite plus every direct child suite and request
  an independent Task 1 review.

### Task 2: Static source proof and fail-closed CLI

**Files:**
- Create: `trading_system/tree_spec/lifecycle_live_resolver_source.py`
- Create: `tools/check_lifecycle_live_resolver_source_parity.py`
- Create: `tests/tree_spec/test_lifecycle_live_resolver_source.py`

**Interfaces:**
- Consumes: explicit retained-source root and the Task 1 vendor module text.
- Produces: schema-valid `VERIFIED`/`BLOCKED` JSON with child reports and
  `ready_for_replay=false`, `ready_for_training=false` on every path.

- [x] Write failing audit tests for source root/commit/blob, leading two-quote
  observation order, corrected-bar fallback/range carry, scan/skip order,
  PENDING fall-through, OPEN child order, ambiguity continuation, ordinary-
  terminal zone suppression, raw-quote forwarding, child identity and malformed
  report/CLI serialization paths.
- [x] Parse only source `_check_live_locked` and project the pinned source
  kernel into the private composition contract. Require accepted proof graphs
  for lifecycle live evidence, pending resolution, post-fill evidence, minimum
  success, protection, ordinary resolution and zone return.
- [x] Implement explicit-root CLI exit `0` only for `VERIFIED`; every error
  path emits valid `BLOCKED` JSON with both readiness flags false.
- [x] Run runtime/audit/child suites and the retained-source CLI; request an
  independent Task 2 review.

### Task 3: Acceptance and bounded handoff

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/architecture/TREE-OUTCOME-IMPLEMENTATION-TRACKER.md`
- Modify: `docs/superpowers/plans/2026-09-14-lifecycle-live-resolver-source.md`
- Create: `agent-exchange/status/<UTC>-codex-lifecycle-live-resolver.md`

**Interfaces:**
- Consumes: clean Task 1/Task 2 reviews, final review and independently rerun
  verification.
- Produces: an explicit bounded acceptance or revision record; no readiness
  promotion.

- [x] Review the complete runtime/audit/docs as a single source-order unit and
  independently rerun the combined tests and explicit-root CLI.
- [x] Obtain an independent final review; resolve any source, inherited-effect,
  precedence, or scope finding before acceptance.
- [x] Record acceptance only if physical source, runtime AST, child graph and
  fail-closed readiness checks all pass. State that caller commit,
  persistence/delivery, replay/dataset/training/model and live trading remain
  outside the accepted scope.
