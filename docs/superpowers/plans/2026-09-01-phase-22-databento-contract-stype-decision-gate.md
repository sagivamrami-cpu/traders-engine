# Phase 22 Databento Contract Stype Decision Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a human-reviewed contract/stype decision gate before any real-key Databento online cost preflight.

**Architecture:** Create a small YAML decision contract, JSON schema, loader, CLI validator, and Phase 21 CLI integration. The gate validates the selected Databento symbol mode and rewrites cost-request symbols/stype only after a human-reviewed decision scoped to cost preflight. It never approves purchase, download, feature construction, training, or trading.

**Tech Stack:** Python 3, PyYAML, jsonschema.

**Spec:** `agent-exchange/reviews/2026-09-01T001000Z-groq-recheck-phase-21-databento-hardening.md`

## Global Constraints

- Do not commit or push during this phase.
- Do not write, print, log, or exchange API keys.
- Do not call Databento live APIs in tests or validators.
- Do not approve any Databento purchase or data download.
- Keep `ORDER_FLOW_SOURCE_DECISION` and `OPTIONS_SOURCE_DECISION` open.
- Keep GC, XAUUSD, and GLD as separate identities.
- Do not guess an options parent symbol.

---

### Task 1: Decision Contract

**Files:**
- Create: `schemas/databento_gc_contract_stype_decision.schema.json`
- Modify: `configs/data/databento-gc-contract-stype-decision-template.yaml`
- Test: `tests/research/test_databento_contract_stype_decision.py`

**Interfaces:**
- Produces: a schema for open and cost-preflight-approved contract/stype decisions.
- Produces: a valid open template that satisfies no online gate.

- [ ] Write failing tests proving the open template is valid but not approved.
- [ ] Write failing tests proving approved decisions require `approved_by`, `decided_at`, `evidence`, `selected_mode`, `selected_symbols`, and cost-preflight-only scope.
- [ ] Write failing tests rejecting `XAUUSD`, `GLD`, empty symbols, and unknown modes.

### Task 2: Loader And Policy Application

**Files:**
- Create: `trading_system/research/databento_contract_stype_decision.py`
- Modify: `trading_system/research/databento_vendor_preflight.py`
- Test: `tests/research/test_databento_contract_stype_decision.py`

**Interfaces:**
- `load_databento_contract_stype_decision(path: Path) -> DatabentoContractStypeDecision`
- `apply_contract_stype_decision(policy: DatabentoVendorPreflightPolicy, decision: DatabentoContractStypeDecision) -> DatabentoVendorPreflightPolicy`

- [ ] Implement loader with schema validation and semantic validation.
- [ ] Implement policy application so online cost requests use the approved `selected_symbols` and `stype_in`.
- [ ] Keep MBO reference-only and not a purchase candidate.

### Task 3: CLI Integration And Validator

**Files:**
- Create: `tools/validate_databento_gc_contract_stype_decision.py`
- Modify: `tools/preflight_databento_gc_vendor.py`
- Modify: `tools/validate_phase21.py`
- Test: `tests/research/test_databento_contract_stype_decision.py`

**Interfaces:**
- CLI validates a decision file and prints a redacted payload.
- Phase 21 online CLI requires `--contract-stype-decision` and validates it before constructing a Databento client.

- [ ] Implement validator CLI.
- [ ] Integrate decision validation into online preflight.
- [ ] Update Phase 21 validator to check the open template and missing-decision block.

### Task 4: Agent Review Routing

**Files:**
- Create: `agent-exchange/inbox/claude-code/2026-09-01T002000Z-claude-code-review-phase-22-contract-stype-gate.md`
- Create: `agent-exchange/inbox/groq/2026-09-01T002500Z-groq-review-phase-22-contract-stype-gate.md`
- Create: `agent-exchange/status/2026-09-01T003000Z-codex-phase-22-implementation-result.md`

**Interfaces:**
- Claude Code reviews implementation/test coverage.
- Groq reviews market-data identity and hidden approval risk.

- [ ] Route review requests with copy/paste prompts.
- [ ] Record status and verification results.

### Self-Review

- Spec coverage: prevents online Databento calls before contract/stype decision.
- Placeholder scan: all tasks name concrete files and interfaces.
- Type consistency: function names match planned integration points.
