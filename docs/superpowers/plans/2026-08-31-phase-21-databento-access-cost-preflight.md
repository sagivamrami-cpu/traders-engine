# Phase 21 Databento Access Cost Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a safe Databento preflight that checks GLBX.MDP3 order-flow/options readiness and estimated costs without downloading market data or approving spend.

**Architecture:** Add a policy-driven Python module that produces a redacted JSON report. Offline mode emits the planned checks and blocks live actions; online mode uses an injected or Databento historical client only for metadata, symbology, and `metadata.get_cost` calls. The report stays blocked for purchase, dataset construction, training, and live trading.

**Tech Stack:** Python 3, PyYAML, jsonschema, optional Databento Python SDK `databento>=0.85,<1`.

**Spec:** `agent-exchange/status/2026-08-31T185800Z-codex-phase-20-acceptance.md`

## Global Constraints

- Do not commit or push during this phase; the human owner will handle git later.
- Do not write, print, log, or exchange API keys.
- Read the Databento key from `DATABENTO_API_KEY` only at runtime.
- Do not call `timeseries.get_range`, batch download APIs, or any API that returns market data.
- Do not approve or execute paid downloads; cost estimates are advisory only.
- Do not treat GC, XAUUSD, and GLD as interchangeable instruments.
- Do not query a GC options parent symbol until the options parent identity is explicitly confirmed.
- Keep `ORDER_FLOW_SOURCE_DECISION` and `OPTIONS_SOURCE_DECISION` open after this phase.
- Keep production dataset construction, production training, promotion, live trading, broker execution, and capital allocation blocked.

---

### Task 1: Policy And Schema

**Files:**
- Create: `configs/data/databento-gc-vendor-preflight.yaml`
- Create: `schemas/databento_gc_vendor_preflight.schema.json`
- Modify: `.gitignore`

**Interfaces:**
- Produces: a YAML policy consumed by `load_databento_vendor_preflight_policy(path: Path)`.
- Produces: a JSON schema validating `DatabentoVendorPreflightReport.to_payload()`.

- [ ] **Step 1: Write a config with GLBX.MDP3 candidate checks**

```yaml
version: databento-gc-vendor-preflight-0.1.0
vendor: DATABENTO
dataset: GLBX.MDP3
canonical_symbol: GC
api_key_env: DATABENTO_API_KEY
max_estimated_cost_usd: 25.0
no_data_download: true
purchase_allowed: false
timeseries_get_range_allowed: false
requests:
  - request_id: gc-trades-1d-cost
    purpose: ORDER_FLOW_COST_ESTIMATE
    schema: trades
    symbols: [GC]
    stype_in: raw_symbol
    start: "2026-08-04T00:00:00Z"
    end: "2026-08-05T00:00:00Z"
  - request_id: gc-mbp10-1d-cost
    purpose: ORDER_FLOW_COST_ESTIMATE
    schema: mbp-10
    symbols: [GC]
    stype_in: raw_symbol
    start: "2026-08-04T00:00:00Z"
    end: "2026-08-05T00:00:00Z"
  - request_id: gc-mbo-1d-cost
    purpose: ORDER_FLOW_HIGH_COST_REFERENCE_ONLY
    schema: mbo
    symbols: [GC]
    stype_in: raw_symbol
    start: "2026-08-04T00:00:00Z"
    end: "2026-08-05T00:00:00Z"
options_parent:
  status: UNCONFIRMED_DO_NOT_QUERY
  candidate_symbols: []
```

- [ ] **Step 2: Add JSON schema constants**

Schema must require `report_version`, `mode`, `status`, `dataset`, `canonical_symbol`, `api_key_source`, `api_key_present`, `download_allowed=false`, `purchase_allowed=false`, `timeseries_get_range_allowed=false`, `estimated_requests`, `blocked_actions`, and `blocked_reasons`.

- [ ] **Step 3: Extend gitignore for raw market data**

Add ignore patterns for `*.dbn`, `*.dbn.zst`, `*.zst`, `*.parquet`, `*.zip`, `raw-data/`, and `market-data/`; preserve fixture exceptions already present.

### Task 2: Tests First

**Files:**
- Create: `tests/research/test_databento_vendor_preflight.py`

**Interfaces:**
- Consumes: `build_offline_databento_vendor_preflight(policy, created_at)`.
- Consumes: `build_online_databento_vendor_preflight(policy, client, created_at, api_key_present=True)`.
- Consumes: CLI `tools/preflight_databento_gc_vendor.py`.

- [ ] **Step 1: Write failing tests for offline safety**

Tests assert offline reports validate, keep downloads/purchases/training blocked, include planned cost requests, keep options parent blocked, and do not leak `DATABENTO_API_KEY`.

- [ ] **Step 2: Write failing tests for injected online client**

Tests use a fake client with `metadata.get_dataset`, `metadata.list_schemas`, `metadata.get_cost`, and `symbology.resolve`. Assert costs are reported and no `timeseries` method is called.

- [ ] **Step 3: Write failing tests for missing API key**

The CLI online mode must emit a sanitized blocked report and exit with status `2` when `DATABENTO_API_KEY` is absent.

### Task 3: Module And CLI

**Files:**
- Create: `trading_system/research/databento_vendor_preflight.py`
- Create: `tools/preflight_databento_gc_vendor.py`
- Modify: `requirements.txt`

**Interfaces:**
- `load_databento_vendor_preflight_policy(path: Path) -> DatabentoVendorPreflightPolicy`
- `build_offline_databento_vendor_preflight(policy, created_at: datetime) -> DatabentoVendorPreflightReport`
- `build_online_databento_vendor_preflight(policy, client, created_at: datetime, api_key_present: bool) -> DatabentoVendorPreflightReport`
- `create_databento_historical_client(api_key_env: str) -> object`

- [ ] **Step 1: Implement policy loading and validation**

Reject missing requests, wrong dataset, non-GC canonical symbols, enabled downloads, enabled purchases, or enabled `timeseries_get_range_allowed`.

- [ ] **Step 2: Implement offline report**

Return status `OFFLINE_PLAN_RECORDED_API_KEY_BLOCKED`, planned requests, `api_key_present=false`, and blocked reasons including `API_KEY_NOT_USED_OFFLINE`.

- [ ] **Step 3: Implement online report through safe client interface**

Call only `client.metadata.get_dataset`, `client.metadata.list_schemas`, `client.symbology.resolve`, and `client.metadata.get_cost`. Mark unknown schemas, failed symbol resolution, or costs above policy maximum as blocked reasons.

- [ ] **Step 4: Implement CLI**

Support `--offline` and `--online-cost-estimate`. Online mode requires `DATABENTO_API_KEY`; when missing, print sanitized JSON and exit `2`.

### Task 4: Validator And Agent Routing

**Files:**
- Create: `tools/validate_phase21.py`
- Create: `tests/research/test_phase21_validator.py`
- Create: `docs/implementation-reports/phase-21-databento-access-cost-preflight.md`
- Create: `agent-exchange/inbox/claude-code/2026-08-31T230000Z-claude-code-review-phase-21-databento-access-cost-preflight.md`
- Create: `agent-exchange/inbox/groq/2026-08-31T230500Z-groq-review-phase-21-databento-access-cost-preflight.md`
- Create: `agent-exchange/status/2026-08-31T231000Z-codex-phase-21-implementation-result.md`

**Interfaces:**
- `tools/validate_phase21.py` must run Phase 20 validation, Phase 21 tests, schema validation, offline CLI smoke, and readiness check.

- [ ] **Step 1: Add validator test**

Assert `python tools/validate_phase21.py` exits successfully and prints `Phase 21 artifacts validated`.

- [ ] **Step 2: Add validator**

Run the focused tests and ensure real-data readiness with GC decisions remains `BLOCKED` with five satisfied and two open items.

- [ ] **Step 3: Route reviews**

Ask Claude Code to review implementation and integration. Ask Groq to challenge market-data/vendor assumptions, paid-call safety, symbol identity, and options-parent handling.

- [ ] **Step 4: Record status**

Publish a status note summarizing commands run, artifacts changed, blocked actions, and remaining human decisions.

### Self-Review

- Spec coverage: the plan handles Databento API access, order-flow/options source discovery, cost safety, key redaction, and unchanged readiness gates.
- Placeholder scan: no task depends on undefined later work.
- Type consistency: policy/report function names match the module interfaces above.
