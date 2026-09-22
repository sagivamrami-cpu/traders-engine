# Full-plan implementation and acceptance tracker

Objective: תמשיך עד אשר תיישם את כל התוכנית.
Authority: TR-TREE-OUTCOME-LEARNING-PLAN-2026-09-08.md; approved existing-repository
baseline and economic target. This tracker does not narrow or replace that plan.

## Current evidence and outstanding requirements

| Plan area | Current authoritative evidence | Remaining acceptance work |
| --- | --- | --- |
| A source intake | tree_spec inventory, safe HTML loader and snapshot contracts; accepted foundation report | Atomic question/diagram completeness belongs to B/D, not inferred from inventory count |
| B existing contracts | Six commit pins, producer identities, economics arithmetic, EMA and reversal source manifests | Full source -> calculation -> feature -> consumer registry, old/new node migration and all source thresholds |
| C vertical replay | EMA/session history, reversal detection/pricing, daily periods/ranges/corrections, causal frame sequence and full low-level source map accepted | Bind causal frames/corrections through public historical map, admission/arbitration and stateful executable path |
| D complete tree | Master lists all L0-L21 families and separate producers | Remaining producer/branch/MTF/memory adapters, all unavailable paths and feed/era matrix |
| E simulation | Strict arithmetic for already-resolved trades | Actual entry/order/expiry/stop/TP1/cost/time-exit simulation, ambiguity/censoring, separate movement outcomes |
| F historical dataset | No new outcome-learning dataset yet | Approved data coverage, small then full replay, checkpoints/resume, all linked tables, audit/lineage/allowlist |
| G models | Legacy experiments retained, not evidence for this tree | Rule/logistic/CatBoost/LightGBM on correct dataset, purged temporal folds, calibration and policy selection |
| H evaluation | No new-tree out-of-sample profitability result | Preregister acceptance and untouched holdout, portfolio/cost/coverage/uncertainty/ablation tests, model card |
| I shadow | No promotion/deployment authorized by this goal | Offline/live parity, drift/cost monitoring and rollback; explicit human gate before transition |
| J extensions | Separate research scope in master plan | Learned management/retrieval/ranker/new candidates require separately defined experiments, not implicit success claims |

All explicit master requirements remain binding. Green component tests do not
close a row whose end-to-end acceptance evidence is absent. Model profitability
is an empirical question, not guaranteed by implementation.

## Execution sequence now

1. Original reversal pricing accepted; maintain source parity and explicit
   distinction between accepted pricing and an admitted/executed trade.
2. Historical level-map construction and source input corrections; complete the
   first vertical producer including downstream acceptance and arbitration.
   Source dependencies and specific temporal pitfalls are recorded in
   HISTORICAL-LEVELMAP-SOURCE-CONTRACT.md; this is a source map, not executable code.
3. Expand dependencies/producers/trace coverage in source order, then simulator,
   historical dataset, model/evaluation and the explicitly gated shadow stage.

Concrete source facts to preserve: chartdesk.tr.atr uses unseeded ewm, unlike
chartdesk.indicators.atr's SMA-seeded RMA. Original stop bands include entry-zone
edges and optional quarter-grid anchoring. Nearby nonpaying levels are obstacles,
not target hits. These are source-specific behavior, not interchangeable formulas.

No automatic GC-futures -> OANDA-XAUUSD mapping. Source spot pricing and futures
data need explicit instrument/basis evidence before a historical replay can claim
faithfulness. Costs, expiry/time-exit, acceptance criteria and final holdout must
be resolved from applicable sources or humans before their respective gates.

## Goal-turn record

- Previous work: progress, not a wait/no-progress turn. The actual working tree
  gained a verified as-of level-reversal detector and source audit; final accepted
  status: agent-exchange/status/2026-09-09T091200Z-codex-level-reversal-asof.md.
- Current continuation: full goal active; no repeated blocking condition. Safe
  source pricing implementation is available and is the next critical-path work.
- Pricing continuation: 197 scoped tests and 1027 integration tests passed;
  source and wrapper task reviews approved. No new outcome dataset or model.
  Source inspection confirms forming daily state is required for level-map
  reconstruction; final daily OHLC must never be retroactively used intraday.
  Broad verification:1399 passed with explicit legacy-validator exclusion.
  Final acceptance: agent-exchange/status/2026-09-09T101048Z-codex-reversal-pricing.md.
  Nonblocking follow-up before CI: configurable pinned-checkout root for parity
  tests, without skipping mandatory audits. Full objective not complete.
- Period/range continuation: new causal DailyPeriod aggregator38tests passed;
  source range dependency sidecar and task reviews in progress. Prior goal turn
  was progress, not a verified wait or no-progress turn.
- A concrete real-data variant question was sent asynchronously to Roee/Sagiv:
  human inbox2026-09-09T102100Z-gc-versus-source-gold.md. Existing GC decision
  and OANDA source rules cannot be silently merged. Synthetic engineering is
  still unblocked; no whole-goal blocked status or narrowed success criterion.
- Period/range acceptance:108new tests,1135integration tests and1507broad tests
  passed; broad run excludes legacy validators. One closure-only grid defect
  fixed with RED/GREEN regression and independent re-review. Final review clean.
  Status:agent-exchange/status/2026-09-09T102806Z-codex-period-ranges.md.
  Current full-plan work remains historical-map assembly/source evidence before
  producer admission and simulator; no new dataset/model yet.
- Correction continuation: source/as-of evidence implementation in progress in
  docs/superpowers/plans/2026-09-09-correction-asof.md. Source inspection found
  the pinned replay hook emits source=replay, which does not satisfy the
  OANDA broker-shape gate. See HISTORICAL-LEVELMAP-SOURCE-CONTRACT.md; do not
  infer faithful family coverage merely from successfully installing a replay
  source. This is not yet attributed as the cause of an earlier training run.
- Correction acceptance:207 focused,1342 integration,1714 broad tests passed
  (legacy validators excluded); source parity passed and task/final reviews
  approved without findings. Status:agent-exchange/status/2026-09-09T104833Z-codex-correction-asof.md.
  No full historical map, simulation, new outcome dataset or trained model yet.
  Next: causal daily-period sequence and daily/weekly/monthly level-map assembly,
  then remaining families and original producer find/admission/arbitration.
- Historical-map continuation: Task1 complete original source graph and Task2
  causal daily/intraday frames accepted after independent reviews. Parent215
  combined tests passed96.46s; graph sourceauditPASS. Task2 review gaps resolved
  with ten added boundary cases and corrected upsampling guard test. No open
  findings. Task3 public map binding in progress; not yet a completed producer,
  dataset or model. Scope plan:2026-09-09-historical-levelmap-core.md.
