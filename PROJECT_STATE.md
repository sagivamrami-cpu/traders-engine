# Current project state — 2026-09-16

This is the startup checkpoint for Yuval and any coding assistant. Update this
file when a workstream is accepted, a blocker changes, or the next action changes.
Full design: [outcome-learning plan](docs/architecture/TR-TREE-OUTCOME-LEARNING-PLAN-2026-09-08.md).
Setup and human-readable handoff: [Yuval handoff](docs/architecture/YUVAL-HANDOFF.md).
Detailed evidence/history: [tracker](docs/architecture/TREE-OUTCOME-IMPLEMENTATION-TRACKER.md).

## Goal and approved decisions

Build a source-faithful historical replay of Sagiv's implemented tree, capture
everything known when it proposes a trade, resolve economic outcomes under an
explicit execution policy, then train/evaluate a model that improves candidate
selection. Net profitability is primary; movement success and MAE/MFE are separate.
Later, dynamic trade management has its own decision trajectories and evaluation.

- Source baseline: six repositories and exact commits in
  `configs/trees/existing-alerts-baseline.json`. HTML documents explain intent;
  pinned executable code supplies the current baseline behavior.
- Price/trade target: `OANDA:XAUUSD` (option A already approved).
- Databento `CME:GC` is cross-market flow context only. Only closed, available
  minute volume/delta/trades; exclude `[2017-01-01, 2017-06-01)`; no cumulative
  CVD, imputation, price alias or automatic tree-branch injection.
- First economic control: `fixed_full_tp1_v1`, original entry/stop and full TP1
  exit, with no optional partials, scaling, BE or trailing.
- General project data access/retention has already been approved in the
  2026-09-15 decisions. Actual source availability/entitlement and coverage must
  still be evidenced. No model promotion, live execution or deployment is approved.
- UTC internally. A bar's opening timestamp does not make its final OHLC available
  at the open. Use bar close and publication/availability cutoffs independently.

## What exists and what it proves

| Area | Current evidence | Remaining work |
|---|---|---|
| Original tree and dependencies | Offline ports, numeric readers, source audits, state/clock/storage/lifecycle components; component acceptance records | Full production-path coverage and historical end-to-end equivalence |
| Closed-bar replay | Bounded supplied-evidence replay Tasks 1–5 accepted, historical 278-test final verification | Admission/producer coverage, real historical inputs and economic simulation |
| Full-tree causal provider and capture | Implemented, local verification recorded | Independent review/acceptance; historical-source adapter |
| GC context sidecar | Implemented; historical 44 focused + 2 manifest tests | Independent review; later data binding; TreeReader has no direct flow port |
| Economics | Explicit Decimal arithmetic for supplied resolved fills | Actual fill/stop/TP1/expiry/time-exit simulation, costs, ambiguity/censoring |
| Data | Local source audit of 147 files; some XAU history and GC archive exist on Roee's machine | Synchronized source-faithful history, news/options and provenance |
| Current selection model | Design selects CatBoost as initial tabular candidate, with rule-only/logistic comparisons | Valid dataset, temporal splits, training, calibration, untouched holdout, net-value evaluation |
| Dynamic management J0–J7 | Material review, mapping and decision workbook | Executable Sagiv rules, state priorities, simulation, decision dataset, policy evaluation |

These are component claims. Old generic GC direction-model results, test totals
from older revisions and historical agent status messages do not certify the new
outcome model. There is no certified current outcome dataset or trained model.

## Resume queue — execute in this order as dependencies permit

1. **Restore/check the environment:** follow the handoff guide, prepare pinned
   source checkouts and run the documented smoke tests. Inspect `git status` and
   new `agent-exchange` results. Historical session/process IDs are not live handles.
2. **Close independent reviews:** full-tree provider (including audit addendum),
   evidence capture, outer-admission review where still unaccepted, then GC context.
   Read the original brief, inspect implementation, obtain an independent reviewer,
   resolve findings, rerun scoped checks and record acceptance. A file in an inbox
   is only a request; it does not launch Claude/Groq or prove either is working.
3. **Restore source access:** Roee/Yuval supply an OANDA connection/export location
   and available news/options archives through a private channel. Engineering owns
   coverage, timestamp/publication, revision, calendar and provenance validation.
   The old request's question about flow identity is superseded by the GC decision.
4. **Specify/implement the historical adapter and small replay:** use the real
   tree readers on causal data; bind GC only as the approved context sidecar.
   Report unavailable families and complete-information eligibility explicitly.
5. **Close the economic contract with Sagiv and Roee:** entry fill rule, expiry,
   time exit, within-bar ordering, fees/spread/slippage/swap, size/point value and
   source evidence. See the exact request below. Missing values block dependent
   market labels, not source review or synthetic engineering.
6. **Build and verify the economic simulator:** preserve policy identity, account
   for unfilled/ambiguous/censored attempts separately, and validate long/short,
   gaps, conflicting touches, costs and time boundaries with synthetic examples.
7. **Build the dataset and model:** small audited replay first, then approved
   history; numeric feature snapshots as of decision time, candidate/episode IDs,
   separate future outcomes and label end times, chronological purged splits,
   declared holdout and costs. Train baselines and selection model only after this.
8. **Continue management J1–J7:** Sagiv's action/state definitions and examples,
   policy catalogue and multi-fill accounting, management-decision data, policy
   evaluation at equal risk, sizing and joint entry/management validation.

Do not wait forever for an unlaunched reviewer. Start an available independent
review tool/agent with the scoped brief, or tell the operator what must be run.
Keep domain-value questions open while advancing independent authorized work.

## Exact open requests and controlling decisions

- Source availability:
  `agent-exchange/inbox/human/2026-09-15T065418Z-human-xauusd-source-profile-required.md`.
- Economic contract:
  `agent-exchange/inbox/human/2026-09-15T104734Z-human-fixed-full-tp1-economic-contract-required.md`.
- Management:
  `docs/architecture/SAGIV-INPUTS-REQUIRED-FOR-PROJECT.md` and
  `docs/architecture/SAGIV-MANAGEMENT-DECISION-WORKBOOK.md`.
- GC authorization:
  `agent-exchange/decisions/2026-09-15T102150Z-human-gc-order-flow-xauusd-context.md`
  and `2026-09-15T103500Z-human-gc-xauusd-context-implementation-approved.md`
  in the same directory.
- General source authorization:
  `agent-exchange/decisions/2026-09-15T073543Z-human-xauusd-access-and-full-information-requirement.md`.
- Review briefs: in both `agent-exchange/inbox/claude-code/` and `inbox/groq/`:
  `2026-09-15T063341Z-codex-full-tree-causal-provider-implementation-review.md`,
  `2026-09-15T063744Z-codex-full-tree-provider-review-addendum.md`,
  `2026-09-15T064800Z-codex-full-tree-evidence-capture-review.md`,
  `2026-09-15T103900Z-codex-gc-xauusd-context-review.md`.

## Memory maintenance

When finishing a task, record actual changes and verification under
`agent-exchange/status/`, update this queue and the implementation tracker, and
link any changed human decision. Keep historical evidence intact. Reconcile stale
inbox requests against later acceptance records before rerunning old tasks.
`docs/architecture/YUVAL-PROJECT-ONBOARDING.html` is the conceptual explanation;
this checkpoint is the current continuation pointer. `.superpowers/sdd/` contains
historical design/review packages and scratch scripts, not startup commands.
