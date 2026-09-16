# Research Design Decision — Economic Target and Existing Baseline

Recorded at: 2026-09-08T18:00:46Z (recording time, not a claimed message timestamp)

Approver: User in the current authenticated conversation; no additional personal identity asserted.

Decision: APPROVED_RESEARCH_DESIGN

Scope: Local research design and its implementation planning only.

## Approval evidence

The user selected the existing implementation: "משתמשים בגרסא שעובדת בrepos ששלחתי".
After the assistant recommended net profitability as the primary objective,
separate movement outcomes, fixed initial management and a selection model before
management learning, the user replied: "הולך עם ההמלצות שלך".

## Accepted decisions

1. Reuse the existing six-repository implementation. Preserve producer/variant,
   source and version identities; do not equate it with every target-HTML clause.
2. Primary evaluation objective: net economic performance under fixed management,
   with risk/activity constraints; accuracy and movement success are not substitutes.
3. Retain continuous net_R and net P&L alongside economic SUCCESS/FAILURE/BREAK_EVEN.
4. Separately retain directional threshold success, MAE/MFE, target sequence and
   time-to-events. These are future targets/outcomes, never pre-entry inputs.
5. Initial economic simulation: entry conditions and initial stop from the engine,
   full exit at TP1, no additions, no partial exits, no optional BE/trailing.
6. Keep original alert-tracking/movement measurements separate and unchanged.
   Their observation horizon can extend beyond the economic TP1 exit; give each
   policy its own outcome end time and version, including temporal split purging.
7. First learn trade selection under fixed management. Management optimization,
   other exits and new candidate generation require separate later experiments.
8. Rejected, unfilled, cancelled, ambiguous and unresolved attempts are not
   automatically losing filled trades. Preserve their states and coverage.

## Pinned source references

The inspected commits below are the reproducible starting references. Selecting
the repos does not prove the same versions are deployed on a live host.

| Repository | Commit |
|---|---|
| traders-engine | b0953a84271a90095437af04ea378a31863a203d |
| trading-floor | d827dd792cbd1d396b4ee325879c63e57388e07a |
| chart-desk | 68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9 |
| model-desk | f1bf8c73a52db0b2e38636ec8360234a29a1a4b6 |
| news-desk | 9130fef594b9b944d8f0530c7bdf291069654a3a |
| options-desk | 52dce4e7815ebdf7ea765169942fd308266a347b |

Source review: `agent-exchange/reviews/2026-09-08T175056Z-codex-existing-alerts-tree-study.md`.

## Not implied by the approval

- No new data-vendor approval, raw-data retention approval, model promotion,
  deployment, live trading, broker execution, capital allocation or publication.
- No approved numerical commissions/spread/slippage, pending expiry or time exit
  beyond what can be explicitly mapped from applicable existing contracts.
- No permission to treat futures prices/units as the CFD venue's prices/units.
- No assertion that >90% success was independently verified or is net profitability.
- No assertion that a trained model, full historical dataset or complete replay exists.

Before economic labels: finalize instrument-aware fill/cost/time-exit contracts,
arbitration and ambiguity policies. Missing economics must fail readiness, not
silently default to free trading or an unlimited hindsight measurement window.

## Next implementation boundary

Phase B maps existing source -> function -> actual consumer -> typed observation
and contract. Phase C demonstrates a small offline as-of replay with delivery and
broker paths disabled. Phase E implements the accepted fixed economic policy and
separate movement measurements. Only then expand to approved historical data and
model fitting. Existing source inventory/PIT validation remain useful foundations.

Canonical design: `docs/architecture/TR-TREE-OUTCOME-LEARNING-PLAN-2026-09-08.md`.
