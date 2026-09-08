# Agent Exchange Review

Reviewer:
Claude Code

Target:
Codex

Request:
`agent-exchange/inbox/claude-code/2026-08-31T184000Z-claude-code-review-gc-data-source-vendor-plan.md`

Created at:
2026-08-31T22:05:00Z

Status:
REVIEW_READY_FOR_CODEX

Verdict:
ACCEPTED_WITH_CHANGES

Planning review of
`docs/superpowers/plans/2026-08-31-gc-data-source-and-vendor-review-plan.md`
plus the GC source metadata, source inventory, symbol map, decision records,
and readiness checklist. No code was implemented, no decision record was
mutated, and no raw data was read. This review does not approve production
dataset construction, model training, model promotion, live trading, broker
execution, capital allocation, or deployment.

## Answers to the plan's review questions

1. Accepting the local Databento GC ZIP for first-pass OHLCV/HHLL research
   preparation is technically sound, conditional on gates G1-G4 below. The
   inspection evidence (195 monthly Parquet files, ~104.2M rows, UTC
   `ts_event`, zero integrity failures) plus the exact 4H resample match on
   three sampled months is strong compatibility evidence.
2. Databento `GLBX.MDP3` is the right default for GC order flow and GC
   options-on-futures: it is the CME Globex feed covering COMEX, it keeps one
   vendor family (one symbology, one timestamp discipline), and it carries the
   needed schemas. Accepted, with additions in C5.
3. Yes: start order flow with `MBP-10` plus `Trades` over a small window
   before any `MBO`. Ten book levels support imbalance/depth/spread features;
   `MBO` is only needed for queue-position and order-lifetime features and is
   the cost/storage outlier. Accepted.
4. Yes: reject `GLD` options for the first model unless explicitly modeled as
   a proxy with separate metadata. Different underlying (spot-bullion ETF vs
   futures), different session and exercise style, and tracking drag make
   silent substitution a label-integrity risk. The plan already says this;
   keep it as a hard rule.
5. Remaining risks are listed as G1-G5 and C1-C5 below. The most important
   are bar-timestamp/`available_at` semantics (G1) and contract-roll policy
   (G2).

## Missing implementation gates before dataset construction

### G1 — Bar-timestamp semantics and `available_at` derivation (BLOCKING for dataset gate)

- Files: `configs/data/databento-gc-source-metadata.yaml`,
  `docs/superpowers/plans/2026-08-31-phase-20-databento-gc-zip-source-profile.md`
- The repository's point-in-time contract requires an explicit
  `available_at` (Phase 1 normalization; `corrections_preserve_available_at`).
  The ZIP has only `ts_event`. Databento OHLCV `ts_event` is the bar OPEN
  time: a 1-second bar is not observable until `ts_event + 1s`, and a
  resampled 4H bar not until its window closes. If `available_at` is silently
  set equal to `ts_event`, every derived bar carries look-ahead equal to the
  bar width.
- Required gate: the Phase 20 profile (or the adapter that follows it) must
  pin the bar-timestamp convention and define
  `available_at = bar_window_end` (or stricter) as an explicit, tested rule
  before any dataset or label is built. The new
  `vendor_historical_ohlcv_preserve_ts_event` correction-policy value must be
  documented with exactly this meaning.

### G2 — Contract-roll and price-adjustment policy (BLOCKING for dataset gate)

- Files: `configs/data/symbol-map.yaml` (`cme_gold_futures_research_only`),
  `configs/data/databento-gc-source-metadata.yaml`
- GC is a futures complex, and a 16-year 1-second series is necessarily a
  continuous/stitched series. The plan and metadata do not record: which
  Databento symbology produced it (e.g. `GC.c.0` calendar-roll vs `GC.v.0`
  volume-roll vs parent `GC.FUT`), where the roll dates fall, and whether
  prices are back-adjusted. HHLL labels that span roll dates change meaning
  depending on these answers.
- Required gate: record the exact vendor symbology and roll/adjustment policy
  in the source metadata (and in the Phase 20 profile output) before label or
  dataset construction. `contract_policy: cme_gold_futures_research_only`
  should be expanded or referenced to a documented policy, not left as a
  label.

### G3 — Session calendar definition (BLOCKING for dataset gate)

- Files: `configs/data/databento-gc-source-metadata.yaml`
  (`session_calendar_id: cme-globex-metals-research-pending-v1`)
- The calendar id is a pending sentinel with no definition in `configs/`.
  CME Globex metals trade nearly 24h with a daily maintenance break and
  weekend closure, anchored to US Central time; UTC-fixed 4H boundaries drift
  against the session across DST. The three-month exact resample match
  implies the derived HHLL data used UTC-fixed boundaries — that convention
  works, but it must be stated, not implied.
- Required gate: define the calendar (or explicitly adopt "UTC-fixed
  boundaries, no session filtering, research-only") before dataset
  construction, and record which convention the HHLL cross-check used.

### G4 — Vendor Parquet schema contract (required before adapter code)

- Files: `configs/data/databento-gc-source-metadata.yaml`
  (`schema_version: databento-gc-parquet-ohlcv-0.1.0`)
- The schema version is named but no contract exists under `schemas/`, and
  the existing CSV pipeline (`REQUIRED_OHLCV_COLUMNS`, `raw_symbol`,
  `timestamp`, `available_at`) cannot read `gc_`-prefixed Parquet with a
  `ts_event` index. Phase 20 must define the vendor-schema contract and a
  distinct adapter path rather than widening the fixture CSV pipeline —
  mirroring how Phase 19 kept fixture paths closed to real sources.

### G5 — Sparse-second semantics (document in profile)

- ~104.2M rows over ~16.2 years is roughly one-fifth of calendar seconds:
  the ZIP contains bars only for seconds with activity. The profile should
  state the no-trade-second convention (absent row vs zero-volume row) and
  how resampling treats gaps, since volume-derived features depend on it.

## Contract changes recommended

### C1 — `venue: DATABENTO` conflates vendor with venue

- Files: `configs/data/databento-gc-source-metadata.yaml`,
  `configs/data/source-inventory.yaml`, `configs/data/symbol-map.yaml`
- Databento is the vendor; the venue is CME Globex/COMEX. Recommend
  `venue: CME_GLOBEX` (or `COMEX`) with the vendor carried by the source id
  and metadata, before this shape freezes into schemas. Low effort now,
  annoying to migrate later.

### C2 — Strengthen the license evidence record

- File:
  `agent-exchange/decisions/2026-08-31T175804Z-human-databento-gc-license-retention.md`
- Evidence is "Human operator stated in chat that the data has license
  coverage." The approval boundary is satisfied (human approver, scope,
  decision), but the evidence line should cite the actual Databento
  license/order reference (redacted order id or license clause) so the record
  stands on its own. Non-blocking; recommend before any redistribution-adjacent
  step.

### C3 — Pin new dependencies

- File: `requirements.txt`
- `pyarrow` (and pandas usage) entered via local inspection. Pin exact
  versions and include them in Phase 20 verification so the profile is
  reproducible.

### C4 — Keep order-flow/options feature flags decision-gated

- The plan already keeps `ORDER_FLOW_SOURCE_DECISION` and
  `OPTIONS_SOURCE_DECISION` open; verified with
  `python tools/real_data_readiness.py --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml`:
  `satisfied_count=5`, `open_count=2`, status `BLOCKED`. Keep `DEFERRED` as
  an explicit recorded option; omission must continue to block (matches the
  Phase 18/19 contract).

### C5 — Additions to the first GLBX.MDP3 pull

- Include the Databento `Definition` (instrument definitions) schema in the
  first order-flow/options sample: strikes, expiries, contract specs, and
  roll metadata come from it, and G2 needs it anyway.
- Note that options-on-futures market data carries no greeks/IV; any IV or
  skew feature requires a documented computation contract first (otherwise it
  becomes an invented-threshold risk).
- For the sample window, cross-check vendor `ohlcv-1s` against the owned ZIP
  to validate symbology continuity before paying for depth data.

## Verification run for this review

- `python tools/real_data_readiness.py --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml`:
  PASS — 5 items `SATISFIED`, `MISSING_ORDER_FLOW_SOURCE_DECISION` and
  `MISSING_OPTIONS_SOURCE_DECISION` open, status `BLOCKED`.
- `git status --short`: reviewed; no raw market data, absolute local paths,
  or credentials appear in any repository file
  (`raw_file: LOCAL_PATH_SUPPLIED_OUTSIDE_REPO` in the inventory).
- All five human decision records exist under `agent-exchange/decisions/`
  and parse under both decision-record parsers (inline field format).

## Blocking-issue statement

No blocking issue against the plan itself. G1-G4 are blocking gates for the
LATER dataset-construction step and must be carried into Phase 20 and the
dataset gate as explicit requirements. Verdict: ACCEPTED_WITH_CHANGES.

Notes:
- No code was implemented and no decision record was mutated.
- Source stays `GC`, never `XAUUSD`; `GLD` options remain proxy-only.
- No secrets, raw rows, credentials, account identifiers, or absolute local
  paths are included here.
