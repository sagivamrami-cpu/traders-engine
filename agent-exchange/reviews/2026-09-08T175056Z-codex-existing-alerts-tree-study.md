# Agent Exchange Review

Reviewer: Codex (primary source review), with three scoped read-only advisers

Target request: User conversation, 2026-09-08: reread the complete HTML and study all six linked repositories before asking Sagiv to redefine existing rules.

Request: Direct user request; no new inbox contract.

Created at: 2026-09-08T17:50:56Z

Status: REVIEW_READY_FOR_CODEX

Verdict: Reuse the existing implementation. The earlier clarification list was too broad. Existing alert semantics, historical replay semantics, and economic training labels are NOT interchangeable.

## Scope and reproducibility

The primary agent read the entire HTML, including both diagrams, all guide tables, open parameters, notes, and scripts as text. No attached JavaScript was executed.

Source: `docs/sources/tr-hybrid-intelligence-tree.html`
SHA256: `f7de3d8cfac6e468268ec79a8b3b990a97d62608a1fbe68b58952534c107f1ad`

Fresh remote default branches were cloned into an isolated temporary directory. Existing sibling worktrees were older and some were dirty; none were pulled, reset, or edited.

| Repository | Inspected commit |
|---|---|
| traders-engine | b0953a84271a90095437af04ea378a31863a203d |
| trading-floor | d827dd792cbd1d396b4ee325879c63e57388e07a |
| chart-desk | 68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9 |
| model-desk | f1bf8c73a52db0b2e38636ec8360234a29a1a4b6 |
| news-desk | 9130fef594b9b944d8f0530c7bdf291069654a3a |
| options-desk | 52dce4e7815ebdf7ea765169942fd308266a347b |

Below, file references are relative to the named repository at that pinned commit. These are source/call-path findings, not certification of deployed services or exhaustive execution coverage of every module.

## 1. What the repositories actually own

- **chart-desk:** indicator calculations, feature drawers, tree, additional candidate producers, plan geometry, admission, tracking, management advice, replay helpers and an MT5 execution adapter.
- **trading-floor:** notification transport, delivery receipts, market clock, trade ledger, advisory risk and reporting. Not the full tree.
- **news-desk:** calendar, announcements, surprise history, catalysts and explanatory context.
- **options-desk:** genuine feed adapters, surfaces, Greeks, IV/RV, GEX proxies, walls, expected moves, event variance and options strategies. Substantial implementation, not a placeholder.
- **model-desk:** LLM consultation, methodological review and research verdict contracts. Its name does not establish a trained trade-quality predictor.
- **traders-engine default branch:** content generation and Notion/Telegram delivery (`run_daily.py:1`, `engine/generate.py:1`). The local research branch in our workspace has additional training-system work; it must not be confused with that remote default branch.

## 2. HTML versus current executable semantics

The HTML explicitly labels itself target architecture. Its implementation notice at line 429 says the then-current runtime has 12 stages and four separate producers, and distinguishes future TR_TREE_V4 from the XAU_BOOK_V4 setup book.

This notice is itself older than the inspected code. Current `chartdesk/tree.py:1` documents Sagiv's September 1 instruction to gather available evidence and then construct a trade:

- `passed` means a stage was consulted, NOT that its condition was positive.
- Missing vector, missing pattern or price between nearby levels does not automatically veto the trade.
- Required data/calendar/geometry failures still block.
- Current stage sequence ends TRIGGER then TARGET (`tree.py:170`).
- Current trigger observes signed close-to-close movement of the last completed bar, with a 0.15 ATR descriptive threshold; it does not veto (`tree.py:1174`).
- AGGRESSIVE_ATR=1.5 and AGGRESSIVE_BARS=3 still exist but are not the active trigger rule.
- Current `tradeplan.MIN_RR=1.2` (`tradeplan.py:57`); the older knowledge document's 1.5 is not current executable truth.
- Some comments inside files also lag implementation. Body and call path outrank a stale description.

Therefore neither mechanically translating the HTML nor mechanically exporting constants reproduces the current alerts.

## 3. Existing definitions that do not need to be reinvented

| Family | Verified implementation | Source |
|---|---|---|
| MTF averages | EMA 5/13/50/200/800; 4h, 1h, 30m, 15m, 5m drawers; ordering, ATR-normalized slopes, separation, compression, cloud relation | chart-desk `tr.py:36`, `features.py:142` |
| EMA cloud | EMA50 +/- standard deviation(close,100)/4 | `tr.py:51` |
| PVSRA | Prior-10-bar mean volume; climax at volume >=2x mean OR range-times-volume >= prior-10 maximum; rising-volume tier >=1.5x when not climax | `tr.py:82` |
| Stopping Volume | Last completed bar, body/range <=0.35, qualifying wick/range >=0.5, volume >=1.5x prior-10 mean | `tree.py:282` |
| Nearby tree levels | Distance <=0.35 ATR; absence is now contextual, not a veto by itself | `tree.py:128`, `:839` |
| W/M | Swing separation and geometric thresholds exist; primary 1h, fallback 15m in tree | `wm.py:1`, `tree.py:774` |
| RVC/GVC | Last two completed opposing-side vectors, first-body recovery, second-bar wick ratio | `checklists.py:77` |
| Vector groups | Same-direction count within last eight completed bars, at least two; 5m/15m nesting and red-to-violet slowdown also drawn | `features.py:343` |
| Level map | Prior days/weeks, opens, ADR/AWR/RD/RW/AMR families, selected EMA/cloud levels, session opens, PSY and quarters, with provenance constraints | `levelmap.py:195` |
| Tree news window | High-impact +/-15 minutes; unreadable calendar blocks | `tree.py:183`, `:710` |
| News desk windows | High -30/+30, Medium -10/+15; distinct policy, with a reachability defect below | news-desk `newsdesk/calendar.py:40` |
| Options | BSM Greeks, SVI surface, RV20, term/skew, GEX/flip, OI walls, straddle/IV expected moves, event variance | options-desk `metrics.py`, `surface.py`, `eventvol.py`, `moves.py` |

Implemented does not mean empirically validated. Code still explicitly labels some thresholds OPEN/research choices. Preserve their provenance and version; do not ask Sagiv to invent the same numbers again.

Vector recovery is not one universal operation: `tr.vector_zones` closes an open body zone on a return overlap after price departed; `checklists.rvc_gvc` measures recovery of the first candle body by the second close; feature M4 reports a midpoint. A printed `RECOVERY="50pct"` does not establish continuous untouched/half/full recovery tracking.

## 4. Actual candidate producers and integration

Current `scripts/market_watch.py` contains:

1. `level_reversal:{5m/15m}` detection and plans (line 1014).
2. `trend_reaction:{5m/15m}` detection and plans.
3. `tree:house` and `tree:strict` walks and plans (line 1237).
4. `engine:intraday` and `engine:swing` via `tradeplan.build_all` (line 1449).

Opposite reversal candidates take precedence over reaction/tree/engine candidates; reaction conflicts also constrain downstream tree/engine candidates. Slots, cooldown, market windows, deduplication and fill revalidation act outside the tree.

Tree variants have a direct publication path; other plan paths use the group queue/writer. A successful walk is not equivalent to an admitted, published, filled or profitable trade.

`brain.build/decide` supplies additional deterministic observations/decisions used in reporting; it is not evidence of a trained unified historical ranker. `_score_entry` is explicitly observational classification and cannot authorize a trade (`market_watch.py:89`).

Dataset identity must include producer, graph/variant, code/config version, instrument/venue, candidate/episode and stage timestamps. Repeated scans are not independent trades.

## 5. Most important outcome discovery

`chartdesk/desk_success.py:9` defines `desk-minimum-2026-09-07`:

| Symbol | Required favorable movement |
|---|---|
| OANDA:XAUUSD | 4 price points, presented as 40 pips |
| OANDA:NAS100USD | 70 points |
| BINANCE:BTCUSDT | 200 dollars |

This measures **minimum directional success**, not client P&L. Identity-bound, chronological proof can remain successful after a later stop. Code distinguishes success, loss, unknown, open, not_entered and below_floor/other states. It also rejects ambiguous or unverified historical evidence in relevant paths.

`tracker.py:3057` stores BE/lock/trailing suggestions separately in `advisory_stop`; it does NOT change the original stop used by desk tracking. This is an intentional documented alerts policy, not automatically a bug.

The MT5 request uses one volume and TP1 as the order TP (`mt5_executor.py:315`). That is yet another contract, not automatic execution of the full alert ladder or optional management.

Consequences:

- Store directional threshold success separately from net economic outcome.
- Do not label a rejected candidate, unfilled plan, expired plan, data failure or unresolved trade as a losing filled trade.
- Net labels require explicit execution/partial/scale/exit/cost rules and exact instrument units.
- No claim here verifies the user-reported >90% success, its denominator, or whether it used this threshold definition. This discovery is a reason to check, not evidence explaining that percentage.

## 6. Feature collection already exists; a training ledger does not follow automatically

`chartdesk/features.py:1` quotes Sagiv's instruction to draw every parameter before deciding. It provides `Reading` and `Table`, with ok/ABSENT/UNREAD/UNBUILT/EXCLUDED states and metadata.

Important limitations for reuse:

- Many numeric readings are formatted/rounded strings or several numbers combined into one string.
- `snapshot()` (line 620) explicitly stringifies values and atomically overwrites `out/features/<symbol>.json`.
- `input_state.persist()` (line 177) adds useful provenance and decision inputs/outputs, but also overwrites the latest per-symbol file. Its feature facts stringify values.
- Other append-only logs do exist; the finding is that THESE snapshots do not themselves retain an immutable every-decision dataset.
- Drawn evidence is not necessarily decision-effective. Current feature metadata defaults to context/effective=false, while matrix/level/plan sections distinguish their consumers. Audit actual consumers instead of flattening all into votes.
- Some readers use current unfinished bars for current market state; others use the last completed bar for evidence. A historical adapter must recreate exactly what was available at each decision, not hand them retrospectively completed higher-timeframe bars.

Recommended export: raw typed values plus statuses, source/available_at/bar-close times, formula version, consumer/role, full consulted/missing/stopped trace, candidate geometry, admission outcome, lifecycle events, and separate outcome labels.

## 7. Existing replay foundations: reuse, then prove parity

- `scripts/replay.py:165`: tree-walk rows with hashes, trace and next-bar entry. It does not replay the complete producer arbitration/admission/management lifecycle.
- Tree still reads current calendar and wall clock (`tree.py:721`); replacing only bar fetches is insufficient.
- Replay records next-bar entry while its attached plan can be built around the tree decision price. Entry/stop/target geometry must share one explicitly defined fill contract.
- `chartdesk/excursion.py:102`: reusable entry-touch, expiry, chronological stop-first resolution, adverse-only fill bar, targets, MFE/MAE and unresolved outcomes.
- Its default expiry uses style, while `tracker._expire_h` also handles tree-specific 8h expiry; baseline parity is required.
- `levelhistory.levels_asof` accepts passed-in history and reports omitted ADR/RD/EMA families. It is not a complete replacement for the live level map. Timestamp filtering alone needs bar-completion semantics: a daily row stamped at session open is not fully known later that same morning.
- A read-only adviser additionally flagged pending-expiry, weekend closeout and partial-before-stop discrepancies in other lifecycle/backtest paths. These require focused reproductions before fixing or certifying parity.

No ten-year replay or training run was performed.

## 8. Coverage against the 22 target layers

This is a functional mapping, not a claim that every small clause in each layer is implemented and integrated.

| HTML layer | Existing basis / remaining qualification |
|---|---|
| L0 Data/provenance | basis, source receipts, feature/input metadata; historical availability and clock parity still needed |
| L1 Market context | matrix, stretch, level map; profile/Databento facts explicitly research-only in input_state |
| L2 MTF | concrete EMA/structure readers including 30m; exact historical warmup/frame completeness needed |
| L3 Vectors | PVSRA, stopping volume, clusters/nesting/first-vector readers exist |
| L4 Memory | vector zones, liquidity pools; not one continuous half/full recovery contract |
| L5 Levels | extensive live map; historical map deliberately omits families |
| L6 Session/events | clocks, PSY/Brinks, calendar; complete shock/post/normalization state not established |
| L7 Structure | swing, HH/HL/LH/LL, W/M and related detectors; multiple implementations use different pivot windows |
| L8 Liquidity | pools/runs/sweeps; not equivalent to measured full-depth order-flow inventory |
| L9 Behaviour | deterministic observations in brain/stretch/pattern readers; full requested speed/phase contract not certified |
| L10 Setups | multiple wired producers and templates, not only one binary walk |
| L11 Order flow | rolling trade/L1 facts and separate shadow evaluator; not the entire 18-item target flow engine |
| L12 Options | substantial calculations and strategies; several scenario/history/uncertainty states remain partial |
| L13 Regime | heuristic/descriptive regimes exist; learned historical engine weighting not established |
| L14 Historical conditional | reporting/statistics/research helpers exist; no verified integrated PIT conditional outcome learner |
| L15 Ranking | deterministic candidate selection/conflicts and options ranking exist; not a trained unified setup ranker |
| L16 Timing | triggers, pending entries, entry zones/revalidation; policy differs between producers |
| L17 Opportunity | descriptive scores/LLM reviews exist; no demonstrated calibrated trade-profit probability |
| L18 Risk | geometry, RR, slots/cooldown and floor advisory risk; not all target account vetoes uniformly integrated |
| L19 Execution | signal tracking, delivery controls, MT5 adapter; differing execution/management contracts |
| L20 Decision | plans, refusals, candidate sources and tracker state; needs immutable joined episode dataset |
| L21 Feedback | outcomes, replay helpers, research review gates; complete automated offline training/promotion chain not established |

## 9. Desk-specific findings relevant to training

### Order flow

`databento_features.Accumulator` computes 30-second trade facts against preceding buckets and L1 quantities; the class docstring's 60-second description is stale. Some unavailable baseline statistics become zero; missing tick size defaults to 1.0. These need availability states for learning.

`orderflow_engine.evaluate` defines trapped-aggressor reversal, absorption proxy and initiative continuation with actual thresholds (delta-z >=1.5, participation-z >=1, efficiency <=0.28 or >=0.55). It includes freshness/sequence/mapping/confirmation gates. A definition is not an integrated producer: no caller of evaluate was found in the inspected chart source/scripts. Input-state Databento fields are explicitly effective=false/research-only.

Ten years of candles do not establish ten years of aggressor tape, depth, OI or chain history. The supplied data manifest must settle availability; none was audited in this task.

### News

`newsdesk/calendar.py:96` filters upcoming events to those not yet released. `blackouts()` calls that filter, so the declared post-release half is not reachable on that path. This was independently source-verified. It does not prove chart's separate +/-15-minute gate has the same defect.

Prospective surprise history records ingestion/revision observations; it is not a ten-year original-release archive. First recorded by the collector is not necessarily first public release. Forecast-only changes are not separately retained on the reviewed path.

### Options

Real calculations exist. Specific target differences include absent OI publication-time/change contracts, single assumed call-positive/put-negative GEX inventory sign, missing unified multi-scenario dealer-state distribution and unavailable long historical chain coverage in the inspected evidence.

Source finalization fills missing OI/volume with zero (`sources/base.py:239`), conflicting with strict unknown-not-zero training semantics. GEX is a modeled proxy, not observed dealer positions. Some chain-quality flags annotate degraded outputs without universally preventing their computation.

The full adviser review also identified inconsistent IV30/expiry selectors and quote/venue clock guards. These are engineering follow-up findings, not requests for Sagiv to re-explain all options mathematics.

### Floor and model desk

Floor stop bands/risk rules exist, but are advisory in the reviewed floor path. `ledger.mark` scores planned geometry, not net filled lifecycle economics.

Floor's `notify._claim_ok` returns true deliberately: lifecycle validation belongs upstream in chart-desk. Do not describe floor as independently verifying trade claims.

Model-desk review contracts reject certain inconsistent LLM verdicts; they are not trade-model training. Claim hashes do not bind all data/code/management versions, and a review verdict is not human model-promotion authority.

## 10. What actually needs Sagiv/Roi input

1. **Baseline confirmation:** use the pinned current alerts behavior, split by producer/variant, unless Sagiv identifies a specific rule that is obsolete. Confirm the actual deployed version and instruments; do not assume the latest remote commit equals deployment.
2. **Primary learning target:** improve directional threshold success, economic net expectancy under fixed management, or both as separate outputs. Do not use one ambiguous SUCCESS flag.
3. **Only if economic labels are selected:** confirm how optional BE/partials/trailing/scale advice becomes executable rules, including expiry and costs. Existing suggestions are a starting point, not missing knowledge.
4. **Only for moving beyond current alerts:** resolve specific HTML/current-code differences, such as continuous recovery/event normalization/dealer scenarios. These do not all have to block initial faithful replay.

Data-coverage inventory, immutable snapshots, time alignment, producer arbitration, deduplication and reproducing identified defects are engineering work. Do not offload them as twenty broad trader-definition questions.

## Recommended next action

Revise the existing training plan in a separately scoped implementation step:

1. Pin the selected alert baseline and its contracts.
2. Adapt existing feature/candidate/lifecycle functions behind offline as-of data and injected clocks; disable all delivery/broker paths.
3. Add typed immutable observations and candidate/lifecycle joins.
4. Reproduce a small set of known decisions and outcomes, including refusals and ambiguous same-bar cases.
5. Only after parity: replay approved historical inputs, establish baseline economics and directional metrics separately, then train a supervised quality filter/ranker and evaluate chronologically out of sample.

No reason was found to discard the source catalog/PIT foundation already added locally. Its role should change from reconstructing undocumented rules to indexing and enforcing the existing implementation's contracts.

## Verification reviewed

Primary independently ran in the isolated trading-floor checkout:

- `python -B -X utf8 tests/test_claim_gate.py` — PASS, 14 tests.
- `python -B -X utf8 tests/test_marketclock.py` — PASS, 22 tests.

These are mocked transport/clock checks only. They do not validate profitability, chart replay, options calculations, all six repos, or production operation.

Primary reread decisive source bodies for feature snapshots, tree rules, market_watch producer paths, desk_success, advisory stops, excursion/replay, MT5 TP1 request, news blackout filtering, options normalization/GEX, and floor claim/mark semantics.

The required shared-context brief command `python -B scripts/team.py brief ../chart-desk` failed on Windows with `ModuleNotFoundError: fcntl`. Canonical shared context and handoff were read directly; no successful ACK was fabricated and no shared files were relinked.

No raw market payloads, secrets, account ledgers or live operational state were needed. No feed calls, model calls, notifications, training, broker orders, deployment, commits or pushes were performed. Existing workspace changes were preserved. This review document is the only new tracked-workspace artifact from this study.
