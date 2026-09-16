# Agent Exchange Request

Target:
Human

Sender:
Codex

Created at:
2026-09-01T13:32:00Z

Status:
NEEDS_HUMAN_APPROVAL

Objective:
Collect the next human decisions required before Codex may implement real GC dataset construction.

Scope:
- Phase 24 created a fail-closed dataset contract only.
- These decisions would let Codex plan the next implementation phase after Claude Code/Groq review.
- Approving this request must still result in explicit decision records under `agent-exchange/decisions/`; this inbox item is not itself approval.

Required inputs:
- `configs/datasets/gc-30m-real-dataset-contract.yaml`
- `docs/implementation-reports/phase-24-gc-dataset-contract.md`
- `agent-exchange/reviews/2026-09-01T174500Z-claude-code-review-phase-24-human-dataset-decisions.md`
- Official CME Gold futures contract/trading-hours reference before finalizing the session calendar:
  - `https://www.cmegroup.com/markets/metals/precious/gold.contractSpecs.html`

Contracts:
- No dataset builder may run until all required gate decisions are explicit.
- No order-flow features may be built until `ORDER_FLOW_SOURCE_DECISION` is approved and `ORDER_FLOW_ERA_MAP` exists.
- No CVD/cumulative features may be used until PIT, fold-local, era-gapped recomputation is approved and implemented.
- Options remain deferred to v2.
- Macro remains blocked until per-source point-in-time and leakage decisions.

Non-negotiables:
- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, or capital allocation
- no secrets, API keys, raw market-data payloads, or local absolute data paths

Deliverables:
Human should answer the decisions below in chat. Codex will then create exact human decision records in `agent-exchange/decisions/` for confirmation.

## Decisions Requested

### D1: First Dataset Bar Boundary

Codex recommendation: approve UTC-fixed 30-minute bars with half-open intervals:

- `[bar_start_utc, bar_end_utc)`
- boundaries on `00` and `30` minutes UTC
- `available_at = bar_end_utc`
- session/calendar information is added as metadata or later features, not used to shift bar boundaries in v1

Why: this is deterministic, DST-stable, easy to align across OHLCV and one-minute order-flow inputs, and easier to compare with external OHLCV providers.

Meaning if approved: Codex can implement a resampling contract and tests for bar timestamps. It still cannot build the real dataset until all other gates are approved.

### D2: Session Calendar Policy

Codex recommendation: approve `cme-globex-metals-research-v1` as the first GC session calendar policy, but require one more implementation step to encode and test the exact CME Globex metals hours and holiday/maintenance rules from an official CME source.

Meaning if approved: Codex can replace the current fixture-only `us-equities-regular-v1` assumption for GC planning. It still cannot use a guessed calendar; exact rules must be encoded and verified.

### D3: Timestamp Role and Timezone Policy

Codex recommendation: approve this policy for v1:

- OHLCV one-second Databento timestamps are interval-start event timestamps.
- Order-flow Parquet `minute` values are minute-start timestamps.
- Any naive `minute` timestamps are treated as UTC wall-clock only after vendor README/profile evidence confirms that assumption.
- `available_at` for a 30m bar is the 30m bar end or stricter.

Meaning if approved: Codex can implement timestamp normalization checks. It still cannot use order-flow rows whose timezone evidence is missing.

### D4: Missing Bar Policy

Codex recommendation: approve fail-closed missing-bar handling:

- OHLCV missing bars: mark the 30m candidate row invalid/excluded.
- Order-flow `volume`, `delta`, `trades` missing for a valid OHLCV bar: keep OHLCV-only row only if the dataset variant explicitly says `order_flow_optional`; otherwise exclude.
- CVD-family missing or era-broken values: always exclude CVD features until the CVD policy is approved.

Meaning if approved: Codex can implement row-quality and exclusion reasons without inventing fill values.

### D5: Roll Policy and Contract Identity

Codex recommendation: keep the first training dataset blocked until a separate contract/stype decision is made. For research, prefer a continuous or stitched GC front-month series only for feature research, not for execution labels or fill truth.

Meaning if approved: Codex can create a dedicated roll-policy decision template. It still cannot treat GC continuous data as executable truth.

### D6: Order-Flow Source Readiness

Codex recommendation: do not approve source readiness yet. First implement `ORDER_FLOW_ERA_MAP` measurement from sanitized metadata only.

Meaning if approved: Codex will keep `ORDER_FLOW_SOURCE_DECISION` open and build an era-map profiler next. No order-flow features will be built yet.

### D7: Label Contract

Codex recommendation: approve outcome-contract labels, not HHLL labels:

- label is based on whether a future trade contract reaches target before stop
- HHLL may remain auxiliary/research-only
- same-bar target/stop remains ambiguous and excluded from training

Meaning if approved: Codex can adapt the existing fixture label contract to the real GC 30m candidate contract later. It still cannot use `hhll_*` files as the main label.

### D8: Split and Embargo Policy

Codex recommendation: approve chronological walk-forward splits only, with embargo around validation/test windows and with the 2017 damaged-aggressor exclusion mask applied identically to every dataset/model variant.

Meaning if approved: Codex can implement split-policy config and validators before training.

### D9: Dataset Construction Authorization

Codex recommendation: do not approve yet.

Meaning: keep `dataset_construction_allowed=false` until D1-D8 and external Phase 24 reviews are accepted.

Verification commands:
- `python tools/validate_phase24.py`
- `python tools/real_data_readiness.py --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml`

Out of scope:
- Do not paste API keys.
- Do not approve options queries.
- Do not approve macro sources.
- Do not approve model training.
- Do not approve model promotion, live trading, broker execution, or capital allocation.

Notes:
Suggested human response format:

```text
D1 approved/rejected/modify: ...
D2 approved/rejected/modify: ...
D3 approved/rejected/modify: ...
D4 approved/rejected/modify: ...
D5 approved/rejected/modify: ...
D6 approved/rejected/modify: ...
D7 approved/rejected/modify: ...
D8 approved/rejected/modify: ...
D9 approved/rejected/modify: ...
```
