# V5 Continuous $1,000 Trade-Management Replay Design

Date: 2026-09-17  
Status: user-approved design, awaiting written-spec review  
Scope: offline research only; no live alert, Telegram, order-routing, fixed-TP1
control, training-readiness or production change

## 1. Objective

Build a causal, continuous-account replay of the existing V4 gold-management
model with:

- initial account equity of $1,000;
- minimum 0.05 lot per leg and at least 0.15 lot per initial basket;
- explicit repeated additions;
- target-state and runner accounting that remains visible after the target leg
  was already used by the early +40-pip partial;
- registered alternatives for the early-protection behavior that flattened
  seven channel-reported TP3 trades before their later TP3 moves;
- dynamic risk, margin, costs and account drawdown instead of summing
  independent daily experiments.

The replay compares management policies on the same causal evidence. It does
not fit thresholds to the final P&L and does not treat channel movement labels
as realized trading returns.

## 2. Preserved V4 baseline

The complete pre-V5 private research directory is preserved at:

`raw-data/account-management-study/snapshots/gold-v4-minlegs-pre-v5-verified-2026-09-17/`

Additional recovery artifacts:

- ZIP: `gold-v4-minlegs-pre-v5-verified-2026-09-17.zip`
- manifest: `gold-v4-minlegs-pre-v5-verified-2026-09-17.manifest.json`
- ZIP SHA-256:
  `5A76338A2A68930B8257DA410191970E47EADFA1DAD332819DD0E060668D19F5`
- verified source/destination file count: 68
- verified source/destination content hashes: identical for every file

V5 must live in a new directory. It must never modify the V4 directory or its
snapshot. V4 reproduction remains a required comparison.

## 3. Evidence behind the experiment

The Telegram outcome study contains 16 reply-linked gold TP3 alerts. Existing
`scaled_retest` management produced only three TP3 events:

- three reached TP3 in replay: #541, #900 and #944;
- seven entered but were flattened after the early +40 partial and before the
  later channel TP3: #464, #733, #822, #984, #1229, #1411 and #1453;
- six never entered: #750, #887, #1198, #1314, #1502 and #1543.

The seven entered misses reached channel TP3 35–180 minutes after the replay
exit, except #822 where TP3 and the BE stop occurred inside the same M5 bar and
their order is unknowable. The primary replay keeps conservative stop-first
ordering; target-first is reported only as an ambiguity sensitivity.

Existing V4 does include the three TP3 partials and their runners:

- TP3 partial realized P&L: $700.575;
- #541 runner: $599.05 realized, versus $841.45 best closed-bar value;
- #944 runner: $60.15 realized, versus $397.35 best closed-bar value;
- #900 runner: $817.60 marked at cutoff, versus $865.20 best closed-bar value.

The issue is therefore premature protection and missing recovery entries, plus
target-state reporting, rather than an automatic full exit at TP3.

The addition audit found 21 children on 13 alerts, +$266.475 gross, but #541
alone contributed +$276.45. All other additions combined lost $9.975. A
$1/oz round-trip cost turns the add version into a $163.525 underperformance
versus the equal-risk no-add control. V5 therefore keeps V4 additions as the
control and tests stricter causal confirmation separately.

## 4. Market and execution identity

- Execution-price identity remains OANDA:XAUUSD.
- Contract normalization remains 100 ounces per 1.00 lot.
- One leg quantum is 0.05 lot = 5 ounces.
- GC flow is not used in this experiment. No Footprint, DOM, delta or CVD is
  fabricated from OHLC.
- M5 inputs must be the already frozen evidence used by V4. Duplicate bars in
  daily windows must be byte/value identical before deduplication; conflicting
  duplicates fail the replay.
- A new entry or addition fills only at the next delivered M5 open after its
  causal confirmation, if every admission condition still holds at that open.
- Stops and targets are evaluated only when the corresponding M5 bar closes.
  If both occur in one bar, the primary result is stop-first and the event is
  marked ambiguous. Target-first is a separate sensitivity.
- Gaps fill at the next delivered executable open; price-risk caps are
  admission estimates and never cap realized gap loss.
- Missing intervals do not receive synthetic bars. Positions remain open and
  are first evaluated at the next delivered observation. The report lists all
  coverage gaps and affected positions.

## 5. Continuous $1,000 account

### 5.1 State

The primary replay starts with:

- cash balance: $1,000;
- realized P&L: $0;
- no open position;
- no daily reset;
- no daily loss stop.

The chronological stream is the stable merge of all unique messages, M5 opens
and M5 closes across August 31–September 17. Open positions, child positions,
cash, current stops, cumulative idea losses and used margin carry across date
boundaries. The study ends at the last delivered close. Remaining positions
are reported both as open marked equity and as an explicit final-liquidation
sensitivity; the marked amount is never called realized profit.

Before each entry or add, current equity is:

`starting cash + cumulative realized P&L + unrealized P&L at the current open`

Risk budgets are percentages of that current equity, not fixed percentages of
the initial $1,000.

### 5.2 Risk regimes

Every management policy runs under both preregistered regimes.

**Primary risk discipline**

- maximum core idea risk: 10% of current equity;
- maximum child risk: 5% of current equity;
- maximum aggregate worst-case risk to active stops: 20% of current equity.

**Coverage stress sensitivity**

- maximum core idea risk: 20% of current equity;
- maximum child risk: 10% of current equity;
- maximum aggregate worst-case risk to active stops: 40% of current equity.

The stress regime exists to expose management behavior with more trades. It is
not the recommended policy. The previous $450/$225/$1,000 V4 sensitivity is
45%/22.5%/100% of a $1,000 account and is excluded as a viable policy.

Risk at admission equals downside to the current stop plus a reserved $1/oz
round-trip cost for the proposed quantity. Realized outputs are reported at
three cost levels—$0, $0.50 and $1 per entered ounce—but admission is frozen to
the conservative $1/oz reserve so the trade population does not change between
cost columns. Stops are never compressed or widened to force a trade through
the budget. If the minimum quantity does not fit, the entry/add is rejected.

### 5.3 Quantity allocation

- Every nonzero leg is an integer multiple of 0.05 lot.
- A profile with TP1/early, TP2 and runner requires at least three legs, hence
  at least 0.15 lot.
- A profile with a separate TP3 leg requires at least four legs, hence at least
  0.20 lot.
- The allocation follows the existing V4 profile fractions, rounded down to
  0.05-lot units; the runner receives the residual units.
- A child may contain one 0.05-lot leg. At 1R that indivisible leg remains open
  and begins trailing. With at least two child units, V4's partial-at-1R and
  runner behavior remains available.
- Maximum core and child quantity is the greatest compliant quantum that fits
  the idea, child, portfolio, cost-reserve and margin gates.

### 5.4 Margin

Primary margin sensitivity uses 1:200 leverage; the comparison uses 1:100.

`required_margin = abs(price × open_ounces) / leverage`

Admission requires at least 20% of current equity to remain free after the new
position. If marked equity becomes nonpositive or required margin exceeds
equity, the replay emits `MARGIN_MODEL_BREACH`, blocks new exposure and reports
the path separately. It does not invent an unverified broker liquidation price.
The final report states that broker margin tiers and stop-out rules remain
unknown.

Financing and swaps are not present in the evidence. Gross/cost-adjusted
results must be labelled as excluding financing; a certified net-return claim
is prohibited.

## 6. Management variants

Every variant shares original alert entry zones, stops and targets, V4 type
routing, causal M5 timing, the quantity/risk contract above, no full TP3 exit,
and one active child per idea at a time.

### C0 — V4 control

- Take the first designated leg at +$4.00 favorable movement when this occurs
  before TP1 and TP1 is at least that far away.
- Move the remainder to BE only after the existing closed-M5 +$4 confirmation.
- Keep V4 type-based target legs, structural trailing, reentry and retest-only
  repeated-child behavior unchanged except for the account/risk contract.

### P1 — delayed protection

- Take exactly one 0.05-lot leg at +$4.00 when eligible.
- Do not move the remaining core to BE merely because M5 closed +$4 favorable.
- Keep the original stop until either:
  1. TP1 is reached; or
  2. a profile-timeframe 2-left/2-right pivot is fully confirmed on the
     protective side of entry.
- At that causal event, advance to entry or the stricter confirmed pivot. Never
  loosen an existing stop.
- Target partials and runner trailing otherwise follow V4.

### R1 — protected recovery entry

- Core management before flat remains C0.
- After an early-protection or profitable structural-stop exit, allow at most
  one recovery entry for the shared idea.
- Recovery is forbidden after an original-loss stop, cancellation, target
  invalidation or expired alert.
- The original profile expiry remains anchored to original publication and is
  never reset by the exit or a Telegram update.
- Recovery requires a newly closed, wholly post-exit profile-timeframe candle
  that retests the original zone, has a directional body and closes beyond the
  zone midpoint in the trade direction.
- Entry is at the immediately following M5 open if price remains on the
  confirmed side, the original stop is valid and all current-equity risk/margin
  gates pass.
- Recovery creates a fresh attempt with the same original target prices and
  no access to later TP3 or channel-success messages.

### U1 — unified candidate

U1 combines P1 and R1, plus stricter additions:

- every balanced or reversal child requires a prior causal
  `STRUCTURE_PROXY_CONFIRMED`; the balanced exception is removed;
- after a child stops, a later child requires a new structure confirmation
  whose confirmation time is strictly after that child exit;
- the existing retest confirmation remains mandatory;
- one child may be active per shared idea, and repeated cycles remain possible
  after closure and fresh reconfirmation;
- core must already be protected, early partial must be complete, local child
  stop must be on the protected side of core entry, and all risk gates must pass;
- no averaging down and no stop widening.

## 7. Target and runner accounting

Target state is independent of leg inventory. On first causal touch, emit:

- `TARGET_REACHED` with target number, target price, event time, bar identity,
  current core/child inventory and ambiguity flag;
- `TARGET_PARTIAL` only if an allocated leg remains to be closed.

Thus TP1 remains visible after the early partial consumed the T1 leg.

For every core runner and child runner, update from each newly closed bar:

- current mark;
- maximum favorable excursion in price, pips, dollars and initial R;
- maximum adverse excursion after TP3;
- highest locked stop value;
- value at final exit/cutoff;
- giveback from best causally observed closed-bar value.

Channel milestones are stored in a separate comparison table. They cannot
mutate position state or P&L and are not model inputs.

## 8. Outputs

The experiment produces:

1. immutable config and source/result hash lock written before results;
2. one full event ledger per variant × risk regime × leverage × ambiguity
   sensitivity;
3. continuous balance, marked-equity, used-margin and risk-to-stop curves;
4. per-alert and per-shared-idea trajectories, including rejected attempts;
5. target funnel: entered, +40, TP1, TP2, TP3 and post-TP3 runner;
6. realized P&L, floating P&L, final-liquidation sensitivity and drawdown;
7. child cycle ordinal, initial/protective-stop exit distinction, MAE/MFE and
   fresh-confirmation lineage;
8. gross and $0.50/$1-per-ounce cost results with turnover;
9. a Hebrew HTML report with the management tree, account timeline, all trades,
   TP3 reconciliation and addition comparison;
10. CSV and JSON exports suitable for independent audit.

The primary headline is C0/P1/R1/U1 under 10%/5%/20%, 1:200, stop-first and
$1/oz costs. Stress, gross, 1:100 and target-first appear only as sensitivities.
If too few trades enter the primary regime, that is the result; no cap is raised
after seeing it.

## 9. Causality and verification

Required automated evidence:

- original V4 files and snapshot hashes remain unchanged;
- C0 reproduces V4 management decisions when account/quantity gates are
  disabled in a dedicated compatibility fixture;
- no event can use a message before publication, a close before bar end or a
  later high/low/close at the bar open;
- stable merge rejects conflicting duplicate bars/messages;
- continuous account inventory, cash, realized/floating P&L, margin and
  risk-to-stop reconcile after every event;
- all nonzero legs are multiples of 0.05 lot, initial baskets are at least 0.15
  or 0.20 as required, and no under-minimum partial remains;
- risk caps are recomputed from current marked equity and include reserved
  costs; gaps may exceed the estimate and remain visible;
- target-state events occur even with zero target-leg quantity;
- runner MFE uses only already closed bars;
- prefix replay and changed-future tests preserve all earlier actions;
- same-bar stop/target ambiguity is separately enumerated;
- every recovery/add references the exact preceding causal confirmations;
- all variant outputs reconcile to the rendered report and exports;
- desktop/mobile HTML, filters, links and right-to-left rendering pass browser
  checks with no page errors.

No result from this in-sample window establishes out-of-sample profitability.
Policy selection requires a future untouched window and actual venue cost,
margin and execution evidence.

## 10. Non-goals

- no live order execution or Telegram mutation;
- no model training or production-readiness claim;
- no invented Footprint/DOM/delta;
- no daily loss stop;
- no price alias between GC and XAUUSD;
- no change to original alert stops or targets;
- no threshold sweep to maximize this window;
- no certified broker net P&L without spread, slippage, financing and margin
  contracts.
