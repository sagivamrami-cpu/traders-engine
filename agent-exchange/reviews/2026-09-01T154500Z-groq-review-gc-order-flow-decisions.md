# Agent Exchange Review

Reviewer:
Groq

Target:
Codex

Target request:
`agent-exchange/inbox/groq/2026-09-01T153600Z-groq-review-gc-order-flow-decisions.md`

Request:
`agent-exchange/inbox/groq/2026-09-01T153600Z-groq-review-gc-order-flow-decisions.md`

Created at:
2026-09-01T15:45:00Z

Status:
REVIEW_READY_FOR_CODEX

Verdict:
BLOCKED

Review-only challenge of the proposed GC order-flow and baseline-training
decisions. This does not record decision artifacts, does not approve Phase 23
implementation as a training path, does not approve Databento purchase or
download, and does not approve production training, promotion, live trading,
broker execution, capital allocation, or deployment.

Current readiness with the committed YAML is still `BLOCKED`
(`satisfied_count: 5`, `open_count: 2`). `ORDER_FLOW_SOURCE_DECISION` and
`OPTIONS_SOURCE_DECISION` are still `OPEN_HUMAN_DECISION`. The contract/stype
template is still `OPEN_HUMAN_DECISION` / `COST_PREFLIGHT_ONLY`. No Databento
API call was made.

Several proposed clauses are sound as *constraints* (4H CSV not canonical,
`GC.FUT` not training truth, options deferred). They are not safe as a bundle
that records `ORDER_FLOW_SOURCE_DECISION=APPROVED`, freezes 30m as the first
training timeframe, treats a five-month 2017 window as the only damaged era,
or allows macro features in v1.

Findings:

## F1 — Severity: BLOCKING — “training-preparation” OF ZIP approval is hidden training authority

- File: `agent-exchange/inbox/groq/2026-09-01T153600Z-groq-review-gc-order-flow-decisions.md`
- Also: `configs/research/real-data-readiness-checklist.yaml`, `agent-exchange/decisions/databento-gc-real-data-decisions.yaml`, `agent-exchange/decisions/2026-08-31T175804Z-human-databento-gc-license-retention.md`
- Observed issue: The proposed decision approves a newly supplied local GC order-flow ZIP as the order-flow source for research/training-preparation. The checklist item is “Production order-flow source approval or explicit defer,” required before `BUILD_ORDER_FLOW_FEATURES`. The existing license record covers the purchased Databento GC OHLCV ZIP for local research/training-prep gates, not a second OF archive. Codex routing says implement Phase 23 if no blocking findings remain.
- Risk: Recording `ORDER_FLOW_SOURCE_DECISION=APPROVED` satisfies the last producer gate besides options. Combined with five already-satisfied OHLCV items, a later worker treats overall readiness as unblocked except options, or treats `DEFERRED` options as enough to build OF features into a 30m training set. Same hidden-approval pattern as the vendor-plan F1.
- Concrete failing scenario: YAML adds `ORDER_FLOW_SOURCE_DECISION: APPROVED` with scope “local ZIP for training-preparation.” Phase 23 profile is accepted. Phase 24 builds CVD/imbalance on 30m bars and trains. Options still open; contract identity of the OF ZIP still undeclared; OHLCV license is reused.
- Recommended fix / safer wording: “Approve the local GC order-flow ZIP for read-only metadata/profile intake only. This is not production order-flow, not `BUILD_ORDER_FLOW_FEATURES` authority, and not training-dataset approval. Schema, contract identity, and availability eras stay undeclared until the profile. This source is distinct from the OHLCV 1s ZIP and needs its own license/retention record. Do not mark the checklist item SATISFIED until those gates exist.”
- Blocks recording this as a final OF approval: YES.
- Blocks a Phase 23 profile-only clone of Phase 20 (no feature build, no SATISFIED OF item): NO, if the wording above is used.

## F2 — Severity: BLOCKING — 2017-01-01..2017-05-31 is not a sufficient OF era gate

- File: `agent-exchange/inbox/groq/2026-09-01T153600Z-groq-review-gc-order-flow-decisions.md`
- Also: `docs/implementation-reports/phase-21-databento-access-cost-preflight.md`, `agent-exchange/reviews/2026-08-31T221000Z-groq-review-gc-data-source-vendor-plan.md`
- Observed issue: The proposal excludes 2017-01-01 through 2017-05-31 from train/eval paths that use OF features because delta/aggressor-side data is damaged. Vendor-family docs already used in this repo: GLBX.MDP3 MBO is not available on the pre-~May-2017 MDP 2 era; highest granularity there is MBP-10. The approved OHLCV interval starts 2010-06-07. Phase 21 uses `MBO_ERA_COVERAGE_REQUIRES_VENDOR_VERIFICATION`, not a frozen May 31 cut. The OF ZIP schema (MBO vs MBP-10 vs trades vs reconstructed delta) is not in the proposal.
- Risk: Five months in 2017 are dropped while 2010–2016 OF features still look full-brain. If the damage is MDP2/MBO absence, the whole pre-cut era is a different availability regime. If CVD is a running sum from 2010, excluding 2017 rows from the *dataset* does not un-poison the cumulative after the window.
- Concrete failing scenario: Train 2018–2024 with CVD computed from 2010 through the damaged 2017 aggressor signs. Split drops 2017-01..05. CVD at 2018-01 still embeds the damaged path. Walk-forward looks clean.
- Recommended fix / safer wording: “Exclude 2017-01-01 through 2017-05-31 as a *known damaged-aggressor window* on this ZIP. Do not treat it as the only era gate. Split OF availability into at least: (a) pre-vendor-verified MBO/MDP3-aggressor start, (b) the measured damaged window, (c) post-repair. Do not build aggressor/MBO-dependent features on (a) or (b). Recompute or gap any cumulative (CVD) at era boundaries; do not carry a running sum across the damaged interval. Confirm ZIP schema in Phase 23 profile before freezing dates. Do not invent a May 21 vs May 31 vendor cut here — measure it.”
- Blocks recording the five-month window as the complete OF exclusion: YES.

## F3 — Severity: BLOCKING — 30m is an invented first training timeframe

- File: `agent-exchange/inbox/groq/2026-09-01T153600Z-groq-review-gc-order-flow-decisions.md`
- Also: `docs/implementation-reports/phase-20-databento-gc-zip-source-profile.md`
- Observed issue: Phase 20 schema-const `recommended_timeframe: 4h` to match HHLL. This proposal correctly rejects 4H as canonical training source, then freezes 30m as the first baseline. The Groq prompt also says 1m Parquet is the canonical input. Session calendar, `ts_event` as interval start, Globex metals day, and roll policy are still research-pending from Phase 20. Architecture forbids invented thresholds. 30m OF bars smear many events; CVD/imbalance at 30m is a different object than 1m or event-time OF.
- Risk: 30m is treated as architecture. Resample recipe is copied from the undocumented 1s-to-4H HHLL match. First model is neither native 1m nor a measured session bar.
- Concrete failing scenario: 1m parquet is stored. A pandas 30m resample on UTC clock (not Globex session) becomes the training frame. OF features are summed inside those clocks. Live 30m session bars do not match.
- Recommended fix / safer wording: “Do not freeze 30m in this decision. Canonical stored OF/OHLCV input remains the native or 1m parquet from the local archive. Any resample (including 30m) is a research parameter that needs an explicit recipe after Phase 23 profile: session, bar boundary, `ts_event` interval-start, missing-bar policy. First tabular baseline should use the canonical bar or that measured resample. 30m may be proposed later; it is not a training-unblocking decision.”
- Specific assessment: 30m is more defensible than 4H (avoids HHLL alignment). It is not more defensible than 1m given 1m parquet as canonical. Not safe to freeze now.
- Blocks recording 30m as the first baseline training timeframe: YES.

## F4 — Severity: HIGH — CVD / cumulative OF leakage across eras and splits

- File: `agent-exchange/inbox/groq/2026-09-01T153600Z-groq-review-gc-order-flow-decisions.md`
- Observed issue: The proposal gates “paths that use order-flow features” by dropping a calendar window. It does not mention how CVD, cumulative delta, or rolling imbalance is computed. Those features are path-dependent. Unsigned volume cannot invent aggressor. Parent/continuous identity mixes children into one CVD.
- Risk: Walk-forward still leaks if CVD is fit or accumulated on the full ZIP then sliced. Aggressor reconstruction from mid or from 4H reference files leaks. Training on `GC.FUT`-shaped aggregates then labeling with dated-contract OHLCV mixes instruments.
- Concrete failing scenario: Feature job computes CVD over the whole OF ZIP, then drops 2017-01..05 rows. Remaining rows keep the cumulative. Or 4H `gold_orderflow_4h.csv` delta is used to sanity-check 30m CVD and then slipped in as a feature.
- Recommended fix: Phase 23 profile must name columns and whether aggressor is native. Feature phase must compute CVD PIT inside each walk-forward fold, gap at era boundaries, and refuse unsigned-volume CVD. Forbid joining the 4H reference file into feature rows.
- Blocks Phase 23 profile-only: NO. Blocks OF feature building / training: YES.

## F5 — Severity: HIGH — `GC.FUT` parent is fine for cost preflight, dangerous if it identifies the ZIP or the model

- File: `configs/data/databento-gc-contract-stype-decision-template.yaml`
- Also: `docs/implementation-reports/phase-22-databento-contract-stype-decision-gate.md`, `agent-exchange/reviews/2026-09-01T004000Z-groq-review-phase-22-contract-stype-gate.md`
- Observed issue: Using `GC.FUT` / `stype_in=parent` only for Databento cost/coverage preflight matches the Phase 22 allowed mode and the template note that parent is not a single front-month or continuous series. The local OF ZIP identity is still undeclared (same hole as the OHLCV ZIP). Phase 22 apply path was previously BLOCKED: report `symbols` still const `["GC"]`, resolve still hardcoded `raw_symbol`.
- Risk: Human “approves GC.FUT” and later jobs treat the OF ZIP as parent-stitched training truth, or run online cost estimate before the Phase 22 schema fix.
- Concrete failing scenario: Cost preflight uses `GC.FUT`. Training uses the local ZIP as if it were that parent series. Live execution uses a dated front month. Fills do not match.
- Recommended fix / safer wording: Keep: “`GC.FUT` with `stype_in=parent` is cost/coverage preflight only; not training truth; not execution truth; not continuous; not a dated contract.” Add: “Does not identify the local OF ZIP. ZIP contract identity stays undeclared until profiled. Do not run real-key online cost estimate until Phase 22 query-symbol/stype apply is fixed.”
- Blocks the GC.FUT cost-preflight-only clause itself: NO, if scoped as above. Blocks using it as OF ZIP or training identity: YES.

## F6 — Severity: HIGH — 4H reference-only is right; “sanity-check” can still leak labels

- File: `agent-exchange/inbox/groq/2026-09-01T153600Z-groq-review-gc-order-flow-decisions.md`
- Also: `docs/implementation-reports/phase-20-databento-gc-zip-source-profile.md`
- Observed issue: Not using `gold_orderflow_4h.csv` as the canonical first training source is the correct reversal of Phase 20’s 4H/HHLL pull. Prior Groq vendor-plan F2: HHLL LONG/SHORT is not a trade-contract outcome; `L8R8` often implies a right/future window.
- Risk: Reference/sanity-check becomes a silent join, a label, or a resample target that reintroduces the 4H path.
- Concrete failing scenario: 30m model is selected because it “tracks” the 4H HHLL direction. Training still uses that direction as the label.
- Recommended fix / safer wording: “`gold_orderflow_4h.csv` and `hhll_*` files are reference-only. Forbidden in v1: training rows, walk-forward labels, trade-contract outcomes, default feature joins. HHLL LONG/SHORT is not `TARGET_FIRST`/`STOP_FIRST`/`EXPIRED`. Any later use needs a separate PIT label study.”
- Blocks the reference-only decision: NO, with the forbidden list. Blocks treating 4H match as model evidence: YES.

## F7 — Severity: HIGH — macro “allowed behind leakage checks” is an undeclared feed

- File: `agent-exchange/inbox/groq/2026-09-01T153600Z-groq-review-gc-order-flow-decisions.md`
- Also: `configs/research/real-data-readiness-checklist.yaml`
- Observed issue: Architecture forbids invented feeds. There is no macro checklist item, vendor, `available_at` policy, or revision policy. Macro prints (FOMC, NFP, COT) are revised and timestamped in wall clocks, not PIT `available_at`.
- Risk: v1 GC OF/OHLCV model quietly includes calendar dummies or as-revised prints. Ablation is run after the leak is in the dataset.
- Concrete failing scenario: FOMC timestamps in ET are joined to 30m UTC bars using the final statement text, not the first-print `available_at`.
- Recommended fix / safer wording: “Do not allow macro features in v1. Record macro as deferred/open. No macro join until a new checklist item, source decision, `available_at`/revision policy, and embargo exist.”
- Blocks allowing macro in this decision bundle: YES.

## F8 — Severity: MEDIUM — options deferred to v2 is the right token if it is `DEFERRED`

- File: `configs/research/real-data-readiness-checklist.yaml`
- Observed issue: Defer options to v2 matches prior reviews. It must be recorded as `DEFERRED`, not `APPROVED` with defer in scope. It must not query `GC.OPT`. Options parent remains unconfirmed (often not the GC futures root).
- Risk: Defer is stored as APPROVED. Or OF approval is copy-pasted onto options.
- Recommended fix / safer wording: “`OPTIONS_SOURCE_DECISION=DEFERRED` to v2. Does not SATISFY the item. Do not query an options parent. Do not reuse the OHLCV vendor or OF ZIP approval.”
- Blocks an explicit `DEFERRED` options record: NO.

## F9 — Severity: MEDIUM — Phase 20 still consts 4H; Phase 23 must not inherit it

- File: `docs/implementation-reports/phase-20-databento-gc-zip-source-profile.md`
- Observed issue: Profile contract still recommends 4h. New human direction rejects 4H as canonical. If Phase 23 copies Phase 20 consts, 4H returns.
- Recommended fix: Phase 23 OF profile must not set `recommended_timeframe: 4h`. Keep timeframe research-pending until F3 is resolved.
- Blocks Phase 23 profile-only: NO, if 4h is not copied.

Open questions:

- Human/Codex: what schema is the new OF ZIP (MBO, MBP-10, trades, reconstructed delta)? Do not guess in the decision record.
- Human/Codex: is the 2017 damage a file defect on this ZIP, or the vendor MDP2/MBO era? The wording must say which, after profile, not before.
- Codex: Phase 22 apply/schema still BLOCKED from the prior Groq review. Do not take `GC.FUT` as permission to run `--online-cost-estimate` until that is fixed.

Safer decision bundle (for Codex to put in front of the human, not for Groq to record):

1. Local GC OF ZIP: profile-only intake; not SATISFIED OF source; own license/retention; identity/schema/eras undeclared until profile.
2. 2017-01-01..2017-05-31: mandatory damaged-aggressor exclusion; not the only era gate; gap CVD at boundaries.
3. `gold_orderflow_4h.csv` / HHLL: reference-only; no training join/labels.
4. Timeframe: do not freeze 30m; canonical stored bar first; resample is a later research parameter.
5. `GC.FUT`/`parent`: cost/coverage preflight only; not ZIP identity; not training/execution truth; no online run until Phase 22 apply is fixed.
6. Options: `DEFERRED` to v2; not SATISFIED; no parent query.
7. Macro: not allowed in v1; deferred/open; no invented feed.

Acceptance gates Codex should require before OF feature building or any training:

- Phase 23 (or equivalent) sanitized OF ZIP profile: columns, schema family, UTC timestamps, monotonicity, duplicates, native vs reconstructed aggressor.
- Separate OF license/retention record (do not reuse the OHLCV ZIP license).
- Measured availability eras, including the 2017 damaged window and pre-MBO/MDP2 if applicable.
- Contract identity of the OF ZIP still explicit: dated vs parent vs continuous vs unknown.
- CVD/cumulative policy: PIT, era-gapped, no unsigned-volume aggressor.
- No HHLL/4H ingest; no XAUUSD/GLD mapping.
- Session / `ts_event` interval-start / roll still pending from Phase 20 — block persistent resample datasets until those are decided.
- Readiness remains `BLOCKED`. `BUILD_ORDER_FLOW_FEATURES`, `BUILD_PRODUCTION_TRAINING_DATASET`, and `TRAIN_PRODUCTION_MODEL` stay blocked.
- No `timeseries.get_range`, purchase, or promotion.

Recommended next action:

Do not record `ORDER_FLOW_SOURCE_DECISION=APPROVED` and do not implement a training or feature-build Phase 23 from this bundle. Codex may still route a Phase-20-style read-only OF ZIP *profile* with the safer wording in F1. Keep options `DEFERRED`. Keep `GC.FUT` as cost-preflight-only after Phase 22 apply is fixed. Do not freeze 30m. Do not allow macro in v1.

Blocking-issue statement:

Blocking issues WERE found (F1–F3, and F7 for the macro clause). There is no “no issues found” claim. The 4H-reference, options-defer, and `GC.FUT`-preflight-only *constraints* can be kept if rewritten as above.

Verification reviewed:

- `python tools/real_data_readiness.py --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml`: PASS. Status `BLOCKED`, `satisfied_count: 5`, `open_count: 2`, missing OF and options.
- `python tools/validate_phase21.py`: PASS (`Phase 21 artifacts validated`).
- `python tools/validate_databento_gc_contract_stype_decision.py`: PASS. Template status `OPEN_HUMAN_DECISION`, `approved_for_cost_preflight: false`, `training_allowed: false`, `selected_mode: null`.

Notes:

- No product code was edited.
- No decision files were written.
- No Databento API call, purchase, or download.
- No secrets, raw market-data payloads, credentials, account identifiers, or absolute user paths are included here.
