# GC Data Source And Vendor Review Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Confirm the supplied Databento GC historical ZIP is suitable for read-only OHLCV research profiling, and choose explicit order-flow and options data-source decisions before any feature work uses those producers.

**Architecture:** Treat the local Databento GC ZIP as the first profiled historical OHLCV source for local research only. Keep order-flow and options as independently gated producers, and keep HHLL files out of the Phase 20 source profile so no derived label becomes a training target by implication.

**Tech Stack:** Python, pandas, pyarrow, Parquet, Databento GC futures data, repository `agent-exchange/` coordination.

**Spec:** `docs/architecture/TR-TREE-TO-TRAINED-MODEL-IMPLEMENTATION-PLAN.md`, `configs/research/real-data-readiness-checklist.yaml`, `configs/data/databento-gc-source-metadata.yaml`

## Global Constraints

- Do not label this source as `XAUUSD`; it is `GC` futures.
- Do not include raw market-data rows, local absolute paths, account data, API keys, or vendor credentials in repository files.
- Do not treat inbox messages as human approval.
- Production training, model promotion, live trading, broker execution, and capital allocation remain blocked.
- Order-flow and options require explicit human decisions: approved source or explicit defer.
- Codex should not commit or push in this pass.

---

## Local Data Compatibility Findings

The supplied Databento GC ZIP was inspected locally.

- ZIP type: monthly Parquet archive for `GC` one-second OHLCV.
- Parquet files: `195`.
- Row count: `104,212,803`.
- Date range: `2010-06-07 00:00:02 UTC` through `2026-08-05 23:59:49 UTC`.
- Columns in every file: `gc_open`, `gc_high`, `gc_low`, `gc_close`, `gc_volume`.
- Index in every file: `ts_event`, `datetime64[ns, UTC]`.
- Quality checks: zero read errors, zero null-containing files, zero invalid OHLC files, zero negative-volume files, zero duplicate-index files, zero non-monotonic files.

The ZIP was also cross-checked against the derived `hhll_4h_L8R8_all` data by resampling monthly 1-second data to 4-hour bars:

- `2012-03`: `136` joined 4H bars, max OHLC price diff `0.0`, max volume diff `0.0`.
- `2018-07`: `137` joined 4H bars, max OHLC price diff `0.0`, max volume diff `0.0`.
- `2025-06`: `131` joined 4H bars, max OHLC price diff `0.0`, max volume diff `0.0`.

Conclusion: the local ZIP is suitable for sanitized GC OHLCV source profiling. It is not an accepted training dataset, does not approve HHLL labels, and is not sufficient by itself for order-flow or options features.

## Vendor Recommendation

Preferred source for both order flow and GC options-on-futures:

- Databento `GLBX.MDP3`.
- Rationale: same vendor family as the current historical source, direct CME Group coverage, includes CME/CBOT/NYMEX/COMEX, supports futures and options, and supports relevant schemas including `MBO`, `MBP-10`, `MBP-1`, `Trades`, and OHLCV.
- Cost note: current public pricing indicates `GLBX.MDP3` Standard around `$179/month`; deep historical MBO/order-book requests can become usage-based by data volume, so a small estimate/sample should precede broad purchase.

Recommended first order-flow scope:

- Start with `MBP-10` for `GC` over a small representative window.
- Use `Trades` alongside `MBP-10` if available under the same pull.
- Defer full `MBO` until the model demonstrates that lower-volume order-book features are useful or until exact storage/cost estimates are approved.

Recommended first options scope:

- Prefer Databento `GLBX.MDP3` options-on-futures for GC/COMEX.
- Pull a limited historical chain window first, aligned to the OHLCV backtest interval.
- Treat any equity/ETF options feed such as `GLD` options as a proxy only, not as a direct substitute for GC options.

Alternatives:

- CME DataMine / CME direct feeds: best provenance, likely higher operational and licensing burden.
- dxFeed: plausible enterprise source for futures/options/order-book data, pricing usually requires sales.
- IBKR: useful for live sanity checks and broker integration, not recommended as the historical training source.
- ThetaData, ORATS, Massive/Polygon: useful for US equity/ETF/index options, not direct GC futures options; only suitable for a separately marked `GLD` proxy path.

## Proposed Next Steps

### Task 1: Accept GC ZIP As First OHLCV Research Source

**Files:**
- Review: `configs/data/databento-gc-source-metadata.yaml`
- Review: `configs/data/source-inventory.yaml`
- Review: `agent-exchange/decisions/databento-gc-real-data-decisions.yaml`

**Interfaces:**
- Consumes: local ZIP inspection evidence above.
- Produces: explicit planning agreement that Phase 20 may profile the GC ZIP and build sanitized source metadata.

- [ ] Verify that the source identity remains `GC`, not `XAUUSD`.
- [ ] Verify that no raw rows or local paths are recorded.
- [ ] Verify that production actions remain blocked.

### Task 2: Record Order-Flow Source Direction

**Files:**
- Future decision file: `agent-exchange/decisions/<timestamp>-human-order-flow-source-decision.md`
- Future YAML update: `agent-exchange/decisions/databento-gc-real-data-decisions.yaml`

**Interfaces:**
- Consumes: vendor review from Claude Code and Groq.
- Produces: either `APPROVED` Databento `GLBX.MDP3` for order flow, or `DEFERRED`.

- [ ] Decide whether first order-flow pull uses `MBP-10`, `Trades`, or full `MBO`.
- [ ] Require exact estimated data size and cost before broad MBO retrieval.
- [ ] Keep order-flow features disabled until the decision exists.

### Task 3: Record Options Source Direction

**Files:**
- Future decision file: `agent-exchange/decisions/<timestamp>-human-options-source-decision.md`
- Future YAML update: `agent-exchange/decisions/databento-gc-real-data-decisions.yaml`

**Interfaces:**
- Consumes: vendor review from Claude Code and Groq.
- Produces: either `APPROVED` Databento `GLBX.MDP3` options-on-futures for GC, `DEFERRED`, or a separate proxy plan.

- [ ] Prefer direct GC options-on-futures over `GLD` proxy data.
- [ ] If a proxy is chosen, create separate proxy metadata and do not mix it silently into GC labels.
- [ ] Keep options features disabled until the decision exists.

### Task 4: Run A Small Vendor Sample Before Full Purchase

**Files:**
- Future report: `agent-exchange/status/<timestamp>-codex-gc-vendor-sample-result.md`

**Interfaces:**
- Consumes: approved or trial-access vendor source.
- Produces: cost, row count, date range, symbols, schemas, and feature-readiness recommendation.

- [ ] Pull a limited sample window only.
- [ ] Report metadata and aggregate counts only.
- [ ] Do not store raw vendor data in `agent-exchange/`.
- [ ] Do not start production training from the sample.

## Sources For Review

- Databento `GLBX.MDP3`: `https://databento.com/datasets/GLBX.MDP3`
- Databento pricing: `https://databento.com/pricing`
- Databento schemas: `https://databento.com/docs/schemas-and-data-formats/schemas`
- CME DataMine: `https://www.cmegroup.com/market-data/datamine.html`
- CME real-time futures/options API: `https://www.cmegroup.com/market-data/real-time-futures-and-options-data-api.html`
- ThetaData pricing: `https://www.thetadata.net/pricing`
- ORATS Data API: `https://orats.com/data-api`
- IBKR market-data pricing: `https://www.interactivebrokers.com/en/pricing/research-news-marketdata.php`
- IBKR TWS API docs: `https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/`
- Massive/Polygon pricing: `https://massive.com/pricing`

## Review Questions

- Is it technically sound to profile the local Databento GC ZIP as the first GC OHLCV research source without approving dataset construction or training?
- Is Databento `GLBX.MDP3` the right default source for both GC order flow and GC options-on-futures?
- Should we start order flow with `MBP-10` and `Trades` before `MBO`?
- Should `GLD` options be rejected for the first model unless explicitly modeled as a proxy?
- What hidden data leakage, licensing, timestamp, session, or symbol-mapping risks remain?
