# Task 2 brief — lifecycle live-evidence source audit

Plan: `docs/superpowers/plans/2026-09-14-lifecycle-live-evidence-source.md`

## Files

- Create: `trading_system/tree_spec/lifecycle_live_evidence_source.py`
- Create: `tools/check_lifecycle_live_evidence_source_parity.py`
- Create: `tests/tree_spec/test_lifecycle_live_evidence_source.py`

## Requirements

Start with normal RED for missing auditor/runtime and mutations of source
identity/blob, physical order/signatures/constants, payload/clock
substitutions, error boundaries and CLI serialization/consistency.

Implement an inert full AST projection plus explicit-root JSON CLI. Fail closed
on every source/audit/CLI error and require false readiness.

Run focused runtime/source suites and retained CLI. The completion report must
not imply live resolver, replay, economic, dataset, training or model
completion.

## Global constraints

- Pin chart-desk commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9` and tracker
  blob `b616b34022e436545d8c1daf85eced51614fd74e`.
- Read/parse retained source only. Never execute it, fetch live/historical
  data, touch a broker, send/deliver a message, mutate a trade, emit an
  outcome or make dataset/model claims.
- Preserve physical selected source order, constants, exception boundaries and
  per-row handling. The only allowed adaptations are source quote-file read to
  `source.quote_payload()` and source wall-clock read to `source.now_epoch()`.
- Auditor verification must prove these selected source items, in this exact
  physical order: `QUOTE_MAX_AGE_S`, `_live_prices`,
  `_historical_replay_safe`, `FORCE_BAR_AGE_S`.
- The runtime target is
  `trading_system/tree_replay/_vendor/lifecycle_live_evidence.py` and it may
  only add a constructor source port outside the selected projection.
- The CLI accepts an explicit retained source root and emits machine-readable
  JSON. Any parse, source, audit, serialization or internal consistency error
  must result in a blocked/false verification and both readiness flags must be
  false. A `verified` result requires source-subset verification and no
  blockers; a blocked result requires source-subset false and at least one
  blocker.
- Tests must mutate source identity/blob, selected order/signatures/constants,
  quote and clock adaptations, exception sets/per-row isolation and CLI
  serialization/consistency. Test only supplied in-memory artifacts.
- No fetch, fallback acquisition, resolver decision, fill, state mutation,
  label, outcome, replay, dataset, model, economics, readiness or delivery
  behavior may be added.

## Context

Read `docs/architecture/LIFECYCLE-LIVE-EVIDENCE-SOURCE-INTAKE.md` first. The
retained source root is supplied by the controller; it is an external,
read-only artifact. Reuse the established fail-closed audit/CLI conventions in
the lifecycle outcome/shelf and lifecycle transitions source auditors, but do
not change those accepted components.

## Required report

Write `task-2-report.md` beside this brief. State changed files, exact test and
CLI commands/results, the source root used, and any blocker. Do not dispatch
subagents, commit, push, or modify unrelated files.
